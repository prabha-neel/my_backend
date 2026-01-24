import logging
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import UserRateThrottle, ScopedRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from .models import Organization, SchoolAdmin
from .serializers import OrganizationSerializer, SchoolAdminProfileSerializer
from django.contrib.auth import get_user_model
User = get_user_model()

# Custom Permissions Import (Inhe check kar lena tumhare permissions.py mein hain)
# from .permissions import IsStaffOrReadOnly, IsOrganizationMember

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────
# 1. Advanced Pagination
# ────────────────────────────────────────────────
class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

# ────────────────────────────────────────────────
# 2. Organization ViewSet (The Core Hub)
# ────────────────────────────────────────────────
class OrganizationViewSet(viewsets.ModelViewSet):
    """
    Enterprise-grade Organization management with multi-tenant isolation.
    - Staff: Full global access.
    - School Admin: Access restricted to their own organization.
    - Security: Throttled, logged, and atomic updates.
    """
    serializer_class = OrganizationSerializer
    pagination_class = StandardPagination
    throttle_classes = [UserRateThrottle, ScopedRateThrottle]
    throttle_scope = 'organization_api'
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'registration_number', 'domain']
    ordering_fields = ['created_at', 'name', 'updated_at']
    ordering = ['-created_at']
    
    def get_permissions(self):
        """Dynamic permission logic: Only staff can create/delete/update orgs."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """
        Implements strict data isolation.
        Prevents SchoolAdmins from seeing other organizations.
        """
        # Optimized with select_related to prevent N+1 queries
        base_qs = Organization.objects.select_related('created_by').all()
        
        user = self.request.user
        if user.is_staff:
            return base_qs

        # Fetch linked organization through the SchoolAdminProfile
        profile = getattr(user, 'school_admin_profile', None)
        if profile:
            return base_qs.filter(id=profile.organization_id)
        
        logger.warning(f"Unauthorized organization access attempt by User ID: {user.id}")
        return base_qs.none()

    @transaction.atomic
    def perform_create(self, serializer):
        """Saves with Audit Trail: who created this org."""
        org = serializer.save(created_by=self.request.user)
        logger.info(f"Organization '{org.name}' (ID: {org.id}) created by User: {self.request.user.id}")

    @transaction.atomic
    def perform_update(self, serializer):
        # Agar models mein 'updated_by' nahi hai, toh sirf save() likho
        serializer.save() 
        logger.info(f"Organization ID: {serializer.instance.id} updated by User: {self.request.user.id}")

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def create_school_with_admin(self, request):
        """
        SUPER-ADMIN ONLY: Creates User -> Creates Organization -> Creates SchoolAdmin Profile.
        As per your Model: Organization needs an 'admin' (User) during creation.
        """
        data = request.data
        try:
            with transaction.atomic():
                # 1. Create/Get the Admin User
                admin_user, created = User.objects.get_or_create(
                    email=data.get('admin_email'),
                    defaults={
                        'username': data.get('admin_username'),
                        'first_name': data.get('admin_first_name', 'Admin'),
                        'is_staff': False,
                    }
                )
                if created:
                    admin_user.set_password(data.get('admin_password', 'TempPass@123'))
                    admin_user.save()

                # 2. Create Organization (Matching your Model fields)
                # Note: Aapke model mein 'admin' field OneToOne hai, isliye hum admin_user pass kar rahe hain.
                new_org = Organization.objects.create(
                    name=data.get('org_name'),
                    org_type=data.get('org_type', 'school'),
                    registration_number=data.get('reg_number', ''),
                    admin=admin_user,
                    created_by=request.user,  # <--- Ye ab Super-Admin ki ID save karega
                    is_active=True
                )
                
                # 3. Create SchoolAdmin Profile (Matching your SchoolAdmin model)
                school_admin = SchoolAdmin.objects.create(
                    user=admin_user,
                    organization=new_org,
                    designation=data.get('designation', 'Principal/Owner'),
                    is_active=True,
                    created_by=request.user # Super-Admin
                )

                return Response({
                    "status": "success",
                    "message": f"Organization '{new_org.name}' and Admin Profile created.",
                    "details": {
                        "org_id": new_org.org_id, # Your auto-generated ID
                        "slug": new_org.slug,
                        "admin_username": admin_user.username
                    }
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Setup failed: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
# ────────────────────────────────────────────────
# 3. SchoolAdminProfile ViewSet (Profile Management)
# ────────────────────────────────────────────────
class SchoolAdminViewSet(viewsets.ModelViewSet):
    """
    Management of School Admin Profiles.
    - Staff: Full access for oversight.
    - User: Strict ownership (can only view/manage their own profile).
    """
    serializer_class = SchoolAdminProfileSerializer
    pagination_class = StandardPagination
    throttle_classes = [UserRateThrottle, ScopedRateThrottle]
    throttle_scope = 'profile_api'
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__email', 'user__first_name', 'organization__name']
    ordering = ['-created_at']

    def get_queryset(self):
        # Prevent N+1 queries by joining user and organization tables
        base_qs = SchoolAdmin.objects.select_related('user', 'organization').all()

        user = self.request.user
        if user.is_staff:
            return base_qs

        # Secure isolation: Only return the logged-in user's profile
        if hasattr(user, 'school_admin_profile'):
            return base_qs.filter(user=user)

        raise PermissionDenied("Access Denied: No associated school admin profile found.")

    @transaction.atomic
    def perform_create(self, serializer):
        # Ensuring profile is linked to the current user and org
        profile = serializer.save(user=self.request.user, created_by=self.request.user)
        logger.info(f"Admin Profile created for User: {self.request.user.id} in Org: {profile.organization.id}")

    @transaction.atomic
    def perform_update(self, serializer):
        serializer.save() 

    # ────────────────────────────────────────────────
    # Extra Enterprise Actions
    # ────────────────────────────────────────────────
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def toggle_active_status(self, request, pk=None):
        """Emergency Action: Only Super-Admins can deactivate a School Admin."""
        profile = self.get_object()
        profile.is_active = not profile.is_active
        profile.updated_by = request.user
        profile.save(update_fields=['is_active', 'updated_by'])
        
        status_str = "activated" if profile.is_active else "deactivated"
        logger.info(f"Admin Profile ID {profile.id} {status_str} by SuperUser {request.user.id}")
        
        return Response({
            'id': profile.id, 
            'is_active': profile.is_active,
            'message': f"Admin profile has been successfully {status_str}."
        }, status=status.HTTP_200_OK)