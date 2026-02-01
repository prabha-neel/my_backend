#views.py
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
from .serializers import (
    OrganizationSerializer, 
    OrganizationDetailSerializer,
    SchoolAdminProfileSerializer,
    SchoolAdminUserSerializer     # <--- Login logic ke liye zaruri hai
)

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

    queryset = Organization.objects.all()
    
    def get_serializer_class(self):
        # Agar user GET request kar raha hai (List ya Detail dekh raha hai)
        if self.action in ['list', 'retrieve']:
            return OrganizationDetailSerializer
        
        # Agar user POST/PUT kar raha hai (Naya school bana raha hai)
        return OrganizationSerializer
    
    def get_permissions(self):
        # 'create' aur 'destroy' sirf Super-Admin (staff) ke liye rakho
        if self.action in ['create', 'destroy']:
            return [permissions.IsAdminUser()]
        
        # 'update' aur 'partial_update' principal bhi kar sakega (agar uska school hai)
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
        """Saves with Audit Trail and auto-upgrades user role to ADMIN."""
        # 1. Organization save karo
        org = serializer.save(created_by=self.request.user)
        
        # 2. Jo user is organization ka admin ban raha hai, uska role update karo
        # Hum serializer.validated_data se admin user nikalenge
        admin_user = serializer.validated_data.get('admin') 
        
        if admin_user:
            # Agar user GUEST hai toh use ADMIN bana do
            if admin_user.role != 'SCHOOL_ADMIN':
                admin_user.role = 'SCHOOL_ADMIN'
                # admin_custom_id generate karne wala logic agar model save par hai 
                # toh ye automatically trigger ho jayega
                admin_user.save()
                logger.info(f"User ID: {admin_user.id} role upgraded to ADMIN for Org: {org.name}")

        logger.info(f"Organization '{org.name}' (ID: {org.id}) created by User: {self.request.user.id}")

    @transaction.atomic
    def perform_update(self, serializer):
        # Agar models mein 'updated_by' nahi hai, toh sirf save() likho
        serializer.save() 
        logger.info(f"Organization ID: {serializer.instance.id} updated by User: {self.request.user.id}")
    
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
        base_qs = SchoolAdmin.objects.select_related('user', 'organization').all()
        user = self.request.user
        
        if user.is_staff:
            return base_qs

        # Filter by user in the SchoolAdmin junction table
        return base_qs.filter(user=user)
    

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