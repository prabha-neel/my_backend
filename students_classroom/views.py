from django.db import transaction
from django.db.models import F, Count
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import UserRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
# Imports from your local files
from .permissions import IsSessionTeacherOrAdmin, CanJoinSession
from .models import ClassroomSession, JoinRequest, Standard, JoinRequestStatus
from .serializers import AssignClassTeacherSerializer
from .serializers import (
    StandardListSerializer,
    SessionCreateSerializer,
    SessionListSerializer,
    SessionDetailSerializer,
    JoinRequestCreateSerializer,
    JoinRequestListSerializer,
    StandardDetailSerializer,
)

# ────────────────────────────────────────────────
# 1. Custom Permissions (Helper for this file)
# ────────────────────────────────────────────────

class IsTeacherOrAdmin(permissions.BasePermission):
    """General access for dashboard listing."""
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and 
            (hasattr(user, "teacher_profile") or hasattr(user, "school_admin_profile"))
        )

# ────────────────────────────────────────────────
# 2. Throttling & Pagination
# ────────────────────────────────────────────────

class JoinSessionThrottle(UserRateThrottle):
    rate = '10/minute'
    scope = 'join_session'

class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

# ────────────────────────────────────────────────
# 3. Standard ViewSet
# ────────────────────────────────────────────────

class StandardViewSet(viewsets.ModelViewSet):
    serializer_class = StandardListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering = ["name"]

    def get_queryset(self):
        user = self.request.user
        # 🔐 Sirf apni organization ki classes dikhao
        # 🎯 Admin Check (Multi-school Safe)
        qs = Standard.objects.all()
        if hasattr(user, 'school_admin_profile') and user.school_admin_profile.exists():
            # Org IDs ki list nikaalo (Safe Way)
            org_ids = user.school_admin_profile.values_list('organization_id', flat=True)
            # Filter mein 'organization_id__in' use karo
            return qs.filter(organization_id__in=org_ids)
        elif hasattr(user, 'teacher_profile'):
            return Standard.objects.filter(organization=user.teacher_profile.organization)
        elif hasattr(user, 'student_profile'):
            return Standard.objects.filter(organization=user.student_profile.organization)
        return Standard.objects.none()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return StandardDetailSerializer
        if self.action == "assign_teacher":
            return AssignClassTeacherSerializer
        return super().get_serializer_class()
    
    @action(detail=True, methods=['post'], url_path='assign-teacher')
    def assign_teacher(self, request, pk=None):
        standard = self.get_object()
        
        # 🎯 HEART PROTECTION: Multi-school admin check
        # Pehle ye line crash kar rahi thi (.organization ki wajah se)
        # Ab hum filter use kar rahe hain jo ki 100% safe hai
        is_authorized_admin = (
            hasattr(request.user, 'school_admin_profile') and 
            request.user.school_admin_profile.filter(organization=standard.organization).exists()
        )

        if not is_authorized_admin:
            return Response(
                {"error": "Aapko is school ke teachers assign karne ka access nahi hai!"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # 🎯 KIDNEY PROTECTION: Baaki serializer logic waisa hi hai jaisa tumne likha tha
        # Isse tumhari purani koi bhi functionality nahi hilegi
        serializer = AssignClassTeacherSerializer(
            standard, 
            data=request.data, 
            partial=True, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({"message": f"Teacher assigned to {standard.name} successfully."})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def create(self, request, *args, **kwargs):
        # 1. Common School ID uthao
        school_id = request.data.get('school_id')
        classes_data = request.data.get('classes', [])

        if not school_id:
            return Response({"error": "Bhai, school_id bhejni zaroori hai!"}, status=400)

        results = []

        # 2. Loop chalao
        for item in classes_data:
            class_name = item.get('name')
            sections_list = item.get('section', []) # ["A", "B", "C"]

            # Agar koi section nahi bheja, toh kam se kam ek empty section ke saath class ban jaye
            if not sections_list:
                sections_list = [None]

            created_sections = []
            
            # 3. Yahan 'Section' alag model nahi hai, isliye hum har section ke liye 
            # Standard model mein hi entry karenge.
            for sec_name in sections_list:
                # 'Standard' model hi use hoga
                obj, created = Standard.objects.get_or_create(
                    organization_id=school_id, 
                    name=class_name,
                    section=sec_name # Yeh model ki field hai
                )
                created_sections.append(sec_name if sec_name else "No Section")

            results.append({
                "class": class_name,
                "sections": created_sections
            })

        return Response({
            "status": "Success",
            "school_id": school_id,
            "processed_data": results
        }, status=201)
# ────────────────────────────────────────────────
# 4. ClassroomSession ViewSet
# ────────────────────────────────────────────────

class ClassroomSessionViewSet(viewsets.ModelViewSet):
    queryset = ClassroomSession.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ["session_code", "target_standard__name"]
    ordering = ["-created_at"]

    def get_permissions(self):
        """Dynamic Permission Allocation"""
        if self.action in ["close_session", "accept_request", "partial_update", "update", "destroy"]:
            # Object-level security check
            return [permissions.IsAuthenticated(), IsSessionTeacherOrAdmin()]
        
        if self.action == "create":
            return [permissions.IsAuthenticated(), IsTeacherOrAdmin()]
            
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        
        # 🎯 Base Queryset (Tumhara purana logic intact hai)
        qs = ClassroomSession.objects.filter(is_deleted=False).annotate(
            db_count=Count('enrollments')
        ).select_related(
            "target_standard", "teacher__user", "organization"
        )

        # 🎯 Admin Logic: Isse line 132 wala error fix ho jayega
        if hasattr(user, "school_admin_profile") and user.school_admin_profile.exists():
            # Org IDs ki list nikaali (Safe way for RelatedManager)
            org_ids = user.school_admin_profile.values_list('organization_id', flat=True)
            
            # Filter mein 'organization' ki jagah 'organization_id__in' use karo
            return qs.filter(organization_id__in=org_ids).annotate(
                seats_remaining=F("student_limit") - F("db_count")
            )

        # 🎯 Teacher Logic (Safe)
        if hasattr(user, "teacher_profile"):
            return qs.filter(teacher=user.teacher_profile).annotate(
                seats_remaining=F("student_limit") - F("db_count")
            )

        return qs.none()
    
    def get_serializer_class(self):
        if self.action == "create":
            return SessionCreateSerializer
        if self.action == "list":
            return SessionListSerializer
        if self.action in ["retrieve", "partial_update", "update"]:
            return SessionDetailSerializer
        return SessionListSerializer

    def perform_create(self, serializer):
        # Serializer khud handle kar lega ki teacher save karna hai ya null
        serializer.save()

    @action(detail=True, methods=["post"], url_path="close")
    def close_session(self, request, pk=None):
        session = self.get_object()
        session.close() 
        return Response({"message": _("Session closed successfully.")}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="accept-request")
    @transaction.atomic
    def accept_request(self, request, pk=None):
        # 1. Session dhoondo URL se
        session = self.get_object()
        request_id = request.data.get("request_id")
        
        if not request_id:
            raise ValidationError({"request_id": _("Request ID is required.")})

        # 2. JoinRequest dhoondo
        join_request = get_object_or_404(
            JoinRequest, pk=request_id, session=session, status=JoinRequestStatus.PENDING
        )

        target_user = join_request.user

        try:
            # 🚀 USERNAME NAHI BADAL RAHE HAIN
            # Seedha model logic call kar rahe hain jo profile (Teacher/Student) banayega
            success, message = session.accept_join_request(join_request)
            
            if not success:
                raise ValidationError(message)

            # Response mein wahi username bhej rahe hain jo user ka pehle se hai
            return Response({
                "message": "Request Accept ho gayi!",
                "username": target_user.username, 
                "status": "ACCEPTED"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            # Operation fail hone par transaction apne aap rollback ho jayega
            raise ValidationError({"error": f"Operation fail ho gaya: {str(e)}"})
        
# ────────────────────────────────────────────────
# 5. JoinRequest ViewSet
# ────────────────────────────────────────────────

class JoinRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == "create" or self.action == "join":
            return JoinRequestCreateSerializer
        return JoinRequestListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = JoinRequest.objects.all().select_related('session', 'user', 'session__organization')

        # 🎯 Step 1: Check karo kya user Admin hai (Strict & Safe)
        # hasattr(user, 'school_admin_profile') check karega relationship hai ya nahi
        # .exists() check karega ki koi school linked hai ya nahi
        if hasattr(user, 'school_admin_profile') and user.school_admin_profile.exists():
            # Yahan humne .organization nahi likha (warna RelatedManager error aata)
            # Humne IDs ki list nikaali hai (Safe Way)
            org_ids = user.school_admin_profile.values_list('organization_id', flat=True)
            return qs.filter(session__organization_id__in=org_ids)

        # 🎯 Step 2: Teacher ke liye check (No change here, safe logic)
        elif hasattr(user, 'teacher_profile'):
            return qs.filter(session__organization=user.teacher_profile.organization)

        # 🎯 Step 3: Normal User (Sirf apni requests dekh sake)
        # Isse normal user ko 500 Error nahi aayega
        return qs.filter(user=user)

    def create(self, request, *args, **kwargs):
        """
        Bhai, ye method tab chalega jab aap bina '/join/' ke hit karoge.
        Ye aapke purane code ko chhede bina response theek kar dega.
        """
        # Hum wahi join wala logic yahan call kar rahe hain
        return self.join(request)
    
    @action(detail=False, methods=["post"], 
            permission_classes=[permissions.IsAuthenticated], # 👈 Isse 403 Forbidden fix ho jayega
            url_path='join',
            throttle_classes=[JoinSessionThrottle])
    def join(self, request):
        """
        🎯 Step-by-step logic Serializer ke andar hai.
        Yahan code ekdum clean rakha hai taaki existing flow na tute.
        """
        # Context mein request pass karna zaroori hai validate method ke liye
        serializer = JoinRequestCreateSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        # Ye line tere Serializer ke validate() ko trigger karegi
        serializer.is_valid(raise_exception=True)
        
        # Ye line tere Serializer ke create() ko trigger karegi
        join_request = serializer.save()
        
        # Response wahi rakha hai jo tujhe chahiye tha
        return Response({
            "id": join_request.id,
            "status": join_request.status,
            "message": "Aapki request bhej di gayi hai! 👍",
            "session_code": join_request.session.session_code
        }, status=status.HTTP_201_CREATED)