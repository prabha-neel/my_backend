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
        if hasattr(user, 'school_admin_profile'):
            return Standard.objects.filter(organization=user.school_admin_profile.organization)
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
        
        # Admin check
        if not hasattr(request.user, 'school_admin_profile') or \
           request.user.school_admin_profile.organization != standard.organization:
            return Response(
                {"error": "Aapko is school ke teachers assign karne ka access nahi hai!"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AssignClassTeacherSerializer(standard, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": f"Teacher assigned to {standard.name} successfully."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
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
        
        # 🎯 Annotation: Database se on-the-fly count mangwa rahe hain
        qs = ClassroomSession.objects.filter(is_deleted=False).annotate(
            db_count=Count('enrollments') # 'enrollments' wahi related_name hai jo model mein hai
        ).select_related(
            "target_standard", "teacher__user", "organization"
        )

        if hasattr(user, "school_admin_profile"):
            org = user.school_admin_profile.organization
            # 🎯 Ab seats_remaining calculate karna safe hai
            return qs.filter(organization=org).annotate(
                seats_remaining=F("student_limit") - F("db_count")
            )

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
        """
        Objective #1, #2, #3: Request ID body se lega aur use Accept karega.
        """
        session = self.get_object()
        request_id = request.data.get("request_id") # Frontend se ID body mein aayegi
        
        if not request_id:
            raise ValidationError({"request_id": _("Request ID is required.")})

        join_request = get_object_or_404(
            JoinRequest, pk=request_id, session=session, status=JoinRequestStatus.PENDING
        )

        # 🎯 Model ka master logic call ho raha hai (Recruitment vs Enrollment)
        success, message = session.accept_join_request(join_request)
        
        if not success:
            raise ValidationError(message)
   
        return Response({"message": message}, status=status.HTTP_200_OK)

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
        qs = JoinRequest.objects.all().select_related('session', 'user')

        if hasattr(user, "teacher_profile"):
            return qs.filter(session__teacher=user.teacher_profile)
        if hasattr(user, "school_admin_profile"):
            return qs.filter(session__organization=user.school_admin_profile.organization)
        return qs.filter(user=user)

    def create(self, request, *args, **kwargs):
        """
        Bhai, ye method tab chalega jab aap bina '/join/' ke hit karoge.
        Ye aapke purane code ko chhede bina response theek kar dega.
        """
        # Hum wahi join wala logic yahan call kar rahe hain
        return self.join(request)
    
    @action(detail=False, methods=["post"], 
            permission_classes=[CanJoinSession], 
            throttle_classes=[JoinSessionThrottle])
    def join(self, request):
        """
        🎯 Step-by-step logic Serializer ke andar hai.
        Yahan code ekdum clean rakhein.
        """
        serializer = JoinRequestCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        join_request = serializer.save()
        
        return Response({
            "id": join_request.id,
            "status": join_request.status,
            "message": "Aapki request bhej di gayi hai! 👍",
            "session_code": join_request.session.session_code
        }, status=status.HTTP_201_CREATED)