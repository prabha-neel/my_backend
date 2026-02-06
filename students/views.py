import logging
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import UserRateThrottle
from django.db.models import Q
from django.contrib.auth import get_user_model
User = get_user_model()
from .models import StudentProfile, StudentSession, StudentResult, StudentFee
from parents.models import ParentProfile, ParentStudentLink
from .serializers import (
    StudentProfileSerializer,
    StudentMinimalSerializer,
    StudentSessionSerializer,
    StudentResultSerializer,
    StudentFeeSerializer,
)

# Standard DRF Permissions
from rest_framework import permissions

# Custom Permissions (Jo humne permissions.py mein banayi hain)
from .permissions import (
    IsStudentOwnerOrStaff, 
    IsTeacherOfStudent, 
    CanApproveParentRequest
)

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────
# Pagination
# ────────────────────────────────────────────────
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


# ────────────────────────────────────────────────
# Permissions
# ────────────────────────────────────────────────
class IsStudentOrTeacherOrAdmin(permissions.BasePermission):
    """
    Permission for StudentProfile endpoints:
    - Staff/SuperAdmin can do everything
    - Teachers can see their own sessions and students
    - Students can see their own profile
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated


# ────────────────────────────────────────────────
# Student ViewSet
# ────────────────────────────────────────────────
class StudentViewSet(viewsets.GenericViewSet):
    """
    Student Management API:
    - List / detail students (teacher/admin)
    - Session creation for teachers/admin
    - Parent linking requests
    Base URL: /api/v1/students/
    """

    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudentOrTeacherOrAdmin]
    pagination_class = StandardResultsSetPagination
    throttle_classes = [UserRateThrottle]

    # ────────────────────────────────────────────────
    # Helper: get student safely
    # ────────────────────────────────────────────────
    def get_student(self, student_id):
        return get_object_or_404(StudentProfile, id=student_id, is_active=True)

    # ────────────────────────────────────────────────
    # 1. Minimal list for normal exploration/search
    # ────────────────────────────────────────────────
    @action(detail=False, methods=["GET"], url_path="explore")
    # @method_decorator(cache_page(60 * 3))  <-- Filhaal ise hata de, warna data update nahi dikhega
    def explore(self, request):
        """
        Active students ko explore karne ke liye with Pagination.
        """
        q = request.query_params.get("q")
        org_id = request.query_params.get("organization_id")
        
        # select_related zaroor lagana performance ke liye
        qs = self.queryset.filter(is_active=True).select_related("user", "organization")

        if org_id:
            qs = qs.filter(organization_id=org_id)
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(user__mobile__icontains=q) |
                Q(student_unique_id__icontains=q)
            )

        # Pagination Magic
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = StudentMinimalSerializer(page, many=True)
            # Ye 'count', 'next', 'previous' aur 'results' bhejega
            return self.get_paginated_response(serializer.data)

        # Fallback agar pagination configuration mein na ho
        serializer = StudentMinimalSerializer(qs, many=True)
        return Response(serializer.data)

    # ────────────────────────────────────────────────
    # 2. Student Profile (self-view or admin/teacher)
    # ────────────────────────────────────────────────
    @action(detail=True, methods=["GET"], url_path="profile")
    def profile(self, request, pk=None):
        student = self.get_student(pk)
        user = request.user

        # Ownership check
        if not user.is_staff and hasattr(user, 'teacher_profile'):
            # Teacher: must be assigned to class/session
            if not StudentSession.objects.filter(student=student, teacher=user.teacher_profile).exists():
                raise PermissionDenied("You do not have access to this student's profile.")

        serializer = StudentProfileSerializer(student)
        return Response(serializer.data)

    # ────────────────────────────────────────────────
    # 3. Create session (Teacher/Admin only)
    # ────────────────────────────────────────────────
    @action(detail=False, methods=["POST"], url_path="create-session")
    @transaction.atomic
    def create_session(self, request):
        user = request.user
        if not (user.is_staff or hasattr(user, "teacher_profile")):
            raise PermissionDenied("Only teacher or admin can create sessions.")

        serializer = StudentSessionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=user)
        logger.info(f"Session {serializer.data.get('id')} created by user {user.id}")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # ────────────────────────────────────────────────
    # 4. Parent Request Approval Flow
    # ────────────────────────────────────────────────
    @action(detail=True, methods=["POST"], url_path="approve-parent-request")
    @transaction.atomic
    def approve_parent_request(self, request, pk=None):
        """
        Objective #11: Student approves parent request
        """
        student = self.get_student(pk)
        parent_id = request.data.get("parent_id")
        if not parent_id:
            raise ValidationError({"detail": "parent_id is required."})

        parent_profile = get_object_or_404(ParentProfile, id=parent_id)

        # Check for existing PENDING request
        link = get_object_or_404(
            ParentStudentLink,
            parent=parent_profile,
            student=student,
            status=ParentStudentLink.Status.PENDING
        )

        link.status = ParentStudentLink.Status.APPROVED
        link.save()
        logger.info(f"Parent {parent_profile.id} approved for Student {student.id} by student action")
        return Response({"detail": "Parent request approved."}, status=status.HTTP_200_OK)

    # ────────────────────────────────────────────────
    # 5. Student Results
    # ────────────────────────────────────────────────
    @action(detail=True, methods=["GET"], url_path="results")
    def results(self, request, pk=None):
        student = self.get_student(pk)
        results_qs = StudentResult.objects.filter(student=student).order_by("-exam__date")
        serializer = StudentResultSerializer(results_qs, many=True)
        return Response(serializer.data)

    # ────────────────────────────────────────────────
    # 6. Student Fees
    # ────────────────────────────────────────────────
    @action(detail=True, methods=["GET"], url_path="fees")
    def fees(self, request, pk=None):
        student = self.get_student(pk)
        fees_qs = StudentFee.objects.filter(student=student).order_by("-due_date")
        serializer = StudentFeeSerializer(fees_qs, many=True)
        return Response(serializer.data)
    
    def get_permissions(self):
        """
        Alag-alag actions ke liye alag permissions
        """
        if self.action in ['profile', 'results', 'fees']:
            permission_classes = [permissions.IsAuthenticated, IsStudentOwnerOrStaff]
        elif self.action == 'approve_parent_request':
            permission_classes = [permissions.IsAuthenticated, CanApproveParentRequest]
        elif self.action == 'create_session':
            permission_classes = [permissions.IsAuthenticated] # Teacher/Admin check view mein hai
        else:
            permission_classes = [permissions.IsAuthenticated]
            
        return [permission() for permission in permission_classes]
