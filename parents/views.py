# parents/views.py
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

# ✅ Fixed: core.models ki jagah get_user_model() use kiya hai
from django.contrib.auth import get_user_model
User = get_user_model()

from students.models import StudentProfile
from .models import ParentProfile, ParentStudentLink
from .serializers import (
    ParentProfileDetailSerializer,
    ParentStudentLinkSerializer,
)
from students.serializers import StudentMinimalSerializer

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
class IsParent(permissions.BasePermission):
    """
    Ensures that the authenticated user has an active ParentProfile.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, "parent_profile") and request.user.parent_profile.is_active


# ────────────────────────────────────────────────
# Parent ViewSet
# ────────────────────────────────────────────────
class ParentViewSet(viewsets.GenericViewSet):
    """
    Industry-level Parent API:
    - Normal User -> Parent conversion
    - Search students by mobile/student_id
    - Send link requests to students
    - View approved linked children
    Base URL: /api/v1/parents/
    """

    queryset = ParentProfile.objects.all()
    serializer_class = ParentProfileDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsParent]
    pagination_class = StandardResultsSetPagination
    throttle_classes = [UserRateThrottle]

    # ────────────────────────────────────────────────
    # Helper: Get current parent safely
    # ────────────────────────────────────────────────
    def get_parent(self) -> ParentProfile:
        parent = get_object_or_404(
            ParentProfile.objects.select_related("user"),
            user=self.request.user,
            is_active=True
        )
        return parent

    # ────────────────────────────────────────────────
    # 1. Parent Profile
    # ────────────────────────────────────────────────
    @action(detail=False, methods=["GET"], url_path="me")
    @method_decorator(cache_page(60 * 5))
    def profile(self, request):
        parent = self.get_parent()
        serializer = ParentProfileDetailSerializer(parent)
        return Response(serializer.data)

    # ────────────────────────────────────────────────
    # 2. Become a Parent (Normal User -> Parent)
    # ────────────────────────────────────────────────
    @transaction.atomic
    @action(detail=False, methods=["POST"], url_path="become")
    def become_parent(self, request):
        if ParentProfile.objects.filter(user=request.user).exists():
            raise ValidationError({"detail": "You are already a registered parent."})
        serializer = ParentProfileDetailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, is_active=True)
        logger.info(f"User {request.user.id} became a Parent.")
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # ────────────────────────────────────────────────
    # 3. Search Students
    # ────────────────────────────────────────────────
    @action(detail=False, methods=["GET"], url_path="search-student")
    def search_student(self, request):
        query = request.query_params.get("q")
        if not query:
            raise ValidationError({"detail": "Please provide mobile number or student ID to search."})

        students_qs = StudentProfile.objects.filter(
            Q(user__mobile=query) | Q(student_unique_id=query),
            is_active=True
        ).select_related("user", "organization")[:50]  # limit for performance

        serializer = StudentMinimalSerializer(students_qs, many=True)
        return Response(serializer.data)

    # ────────────────────────────────────────────────
    # 4. Send Link Request to Student
    # ────────────────────────────────────────────────
    @action(detail=False, methods=["POST"], url_path="send-request")
    @transaction.atomic
    def send_request(self, request):
        student_id = request.data.get("student_id")
        if not student_id:
            raise ValidationError({"detail": "student_id is required."})

        parent = self.get_parent()
        if ParentStudentLink.objects.filter(parent=parent, student_id=student_id).exists():
            raise ValidationError({"detail": "Request already sent or link exists."})

        ParentStudentLink.objects.create(
            parent=parent,
            student_id=student_id,
            status=ParentStudentLink.Status.PENDING
        )
        logger.info(f"Parent {parent.id} sent link request to Student {student_id}.")
        return Response({"detail": "Request sent. Waiting for approval."}, status=status.HTTP_201_CREATED)

    # ────────────────────────────────────────────────
    # 5. View Linked Children
    # ────────────────────────────────────────────────
    @action(detail=False, methods=["GET"], url_path="my-children")
    @method_decorator(cache_page(60 * 3))
    def my_children(self, request):
        parent = self.get_parent()
        links_qs = ParentStudentLink.objects.filter(
            parent=parent,
            status=ParentStudentLink.Status.APPROVED
        ).select_related("student__user", "student__organization")

        # Paginate results
        page = self.paginate_queryset(links_qs)
        if page is not None:
            serializer = ParentStudentLinkSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ParentStudentLinkSerializer(links_qs, many=True)
        return Response(serializer.data)
