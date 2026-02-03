import uuid
from datetime import timedelta
from typing import Optional, Tuple
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Q, Manager, QuerySet
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from .constants import SessionStatus, JoinRequestStatus


# =============================================================================
# Constants (better than TextChoices in many production codebases)
# =============================================================================

class SessionStatus:
    ACTIVE = "ACTIVE"
    FULL = "FULL"
    EXPIRED = "EXPIRED"
    CLOSED = "CLOSED"

    CHOICES = (
        (ACTIVE, _("Active")),
        (FULL, _("Full")),
        (EXPIRED, _("Expired")),
        (CLOSED, _("Closed")),
    )

    TERMINAL_STATES = {EXPIRED, CLOSED}


class JoinRequestStatus:
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

    CHOICES = (
        (PENDING, _("Pending")),
        (ACCEPTED, _("Accepted")),
        (REJECTED, _("Rejected")),
    )

class SessionPurpose:
    STUDENT_ADMISSION = "STUDENT"
    TEACHER_RECRUITMENT = "TEACHER"

    CHOICES = (
        (STUDENT_ADMISSION, _("Student Admission")),
        (TEACHER_RECRUITMENT, _("Teacher Recruitment")),
    )

# =============================================================================
# Models
# =============================================================================

class Standard(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="standards",
        null=True,  # Optional: Agar aap global standards bhi rakhna chahte ho
        blank=True,
        verbose_name=_("Organization"),
    )
    name = models.CharField(
        max_length=50,
        verbose_name=_("Standard / Grade"),
        help_text=_("e.g. Class 8, Grade 10, STD XII"),
    )
    section = models.CharField(
        max_length=10, 
        blank=True, 
        null=True
    ) # A, B, C
    class_teacher = models.ForeignKey(
        "teachers.Teacher", # String use karo circular import se bachne ke liye
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_standards",
        verbose_name=_("Class Teacher"),
    )
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Standard")
        verbose_name_plural = _("Standards")
        ordering = ["name"]
        unique_together = ('organization', 'name', 'section')
        indexes = [models.Index(fields=["is_active", "name"])]

    def __str__(self) -> str:
        return self.name


class ClassroomSession(models.Model):
    # ── Relations ──────────────────────────────────────────────────────────────
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classroom_sessions",
        verbose_name=_("Organization"),
        help_text=_("Leave empty for independent / personal classes"),
    )
    teacher = models.ForeignKey(
        "teachers.Teacher",
        on_delete=models.CASCADE,
        null=True,
        blank=True,        
        related_name="classroom_sessions",
        verbose_name=_("Teacher"),
    )
    target_standard = models.ForeignKey(
        Standard,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sessions",
        verbose_name=_("Target Standard"),
    )

    # ── Core identifiers & rules ──────────────────────────────────────────────
    session_code = models.CharField(
        max_length=10,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name=_("Session Code"),
    )
    title = models.CharField(
        max_length=120,
        blank=True,
        verbose_name=_("Session Title (optional)"),
        help_text=_("e.g. Science Marathon, Algebra Crash Course"),
    )
    student_limit = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(1)],
        verbose_name=_("Maximum Students"),
    )
    expires_at = models.DateTimeField(verbose_name=_("Expires At"))

    # ── State ─────────────────────────────────────────────────────────────────
    purpose = models.CharField(
        max_length=10,
        choices=SessionPurpose.CHOICES,
        default=SessionPurpose.STUDENT_ADMISSION,
        db_index=True,
        verbose_name=_("Session Purpose"),
    )
    status = models.CharField(
        max_length=10,
        choices=SessionStatus.CHOICES,
        default=SessionStatus.ACTIVE,
        db_index=True,
        verbose_name=_("Status"),
    )

    # ── Audit fields ──────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Classroom Session")
        verbose_name_plural = _("Classroom Sessions")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session_code", "status"]),
            models.Index(fields=["teacher", "status", "expires_at"]),
            models.Index(fields=["organization", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(expires_at__gt=models.F("created_at")), 
                name="session_expires_after_creation",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.session_code} • {self.target_standard} ({self.status})"

    def clean(self):
        if self.expires_at and self.expires_at <= timezone.now():
            raise ValidationError(_("Expiration time must be in the future."))

    def save(self, *args, **kwargs):
        if not self.session_code:
            self.session_code = f"CLS-{uuid.uuid4().hex[:6].upper()}"

        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=4)

        # First save → then sync status (because we need PK)
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new or kwargs.get("update_fields") is None:
            self.refresh_from_db()
            self._sync_status(save=False)

    # -------------------------------------------------------------------------
    # Business logic
    # -------------------------------------------------------------------------

    @cached_property
    def current_student_count(self) -> int:
        return self.enrollments.filter(is_active=True).count()

    @property
    def is_joinable(self) -> bool:
        return (
            self.status == SessionStatus.ACTIVE
            and timezone.now() < self.expires_at
            and self.current_student_count < self.student_limit
        )

    def _sync_status(self, save: bool = True) -> None:
        now = timezone.now()

        if now >= self.expires_at:
            new_status = SessionStatus.EXPIRED
        elif self.current_student_count >= self.student_limit:
            new_status = SessionStatus.FULL
        else:
            new_status = SessionStatus.ACTIVE

        if new_status != self.status:
            self.status = new_status
            if save:
                self.save(update_fields=["status", "updated_at"])

    def sync_status(self):
        """Public method – can be called from signals, views, celery, etc."""
        self.refresh_from_db()
        self._sync_status(save=True)

    @transaction.atomic
    def accept_join_request(self, join_request) -> Tuple[bool, str]:
        """
        Atomic operation: 
        Checks purpose -> If STUDENT: Enroll as Student | If TEACHER: Recruit as Teacher.
        Uses SELECT FOR UPDATE to prevent over-booking race conditions.
        """
        if join_request.status != JoinRequestStatus.PENDING:
            return False, "Request is no longer pending"

        # Lock session to prevent race conditions
        session = ClassroomSession.objects.select_for_update().get(pk=self.pk)
        session._sync_status(save=False)

        if not session.is_joinable:
            return False, f"Session is {session.get_status_display()}"

        # ── Step 1: Handle based on Session Purpose ──────────────────────────
        if self.purpose == SessionPurpose.TEACHER_RECRUITMENT:
            # 🟢 TEACHER RECRUITMENT LOGIC
            from teachers.models import Teacher
            
            profile, created = Teacher.objects.get_or_create(
                user=join_request.user,
                defaults={
                    "organization": session.organization,
                    "is_active_teacher": True,
                    "is_verified": True,
                },
            )
            if not created:
                # Agar user pehle se teacher hai toh bas organization update/link kar do
                profile.organization = session.organization
                profile.save(update_fields=["organization"])
            
            msg = "Admin successfully recruited as Teacher"

        else:
            # 🔵 STUDENT ADMISSION LOGIC (Replace sirf is part ko karein)
            from students.models import StudentProfile 
            import datetime
            import random
            
            # 1. Check if profile already exists
            student = StudentProfile.objects.filter(user=join_request.user).first()

            if student and student.current_standard == session.target_standard:
                # 🛑 Data Protection: Already in this class, don't touch profile
                msg = f"Student is already a permanent member of {session.target_standard.name}."
            else:
                # 2. Create New Profile or Update existing one
                year = datetime.date.today().year
                org_prefix = session.organization.name[:3].upper() if session.organization else "GEN"
                rand_num = random.randint(1000, 9999)
                generated_id = f"{year}-{org_prefix}-{rand_num}"

                student, created_profile = StudentProfile.objects.get_or_create(
                    user=join_request.user,
                    defaults={
                        "organization": session.organization,
                        "student_unique_id": generated_id,
                        "is_active": True,
                        "current_standard": session.target_standard,
                    },
                )

                if not created_profile:
                    student.current_standard = session.target_standard
                    if not student.organization:
                        student.organization = session.organization
                    student.save(update_fields=['current_standard', 'organization'])
                
                msg = f"Student successfully enrolled in {session.target_standard.name}"

            # 3. Always create/get session enrollment tracking
            enrollment, created_enroll = SessionEnrollment.objects.get_or_create(
                student=student,
                session=session,
                defaults={"is_active": True},
            )

            if not created_enroll:
                return False, "Student is already enrolled in this specific session"

        # ── Step 2: Finalize Join Request & Session Status ───────────────────
        join_request.status = JoinRequestStatus.ACCEPTED
        join_request.save(update_fields=["status", "updated_at"])

        # After enrollment/recruitment -> update session status (like FULL)
        session._sync_status(save=True)

        return True, msg


class SessionEnrollment(models.Model):
    student = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.CASCADE,
        related_name="session_enrollments",
    )
    session = models.ForeignKey(
        ClassroomSession,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, db_index=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Enrollment")
        verbose_name_plural = _("Enrollments")
        unique_together = (("student", "session"),)
        indexes = [
            models.Index(fields=["student", "is_active"]),
            models.Index(fields=["session", "is_active"]),
        ]

    def __str__(self):
        return f"{self.student} @ {self.session.session_code}"

    def deactivate(self):
        if self.is_active:
            self.is_active = False
            self.deactivated_at = timezone.now()
            self.save(update_fields=["is_active", "deactivated_at"])


class JoinRequest(models.Model):
    session = models.ForeignKey(
        ClassroomSession,
        on_delete=models.CASCADE,
        related_name="join_requests",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="classroom_join_requests",
    )
    status = models.CharField(
        max_length=10,
        choices=JoinRequestStatus.CHOICES,
        default=JoinRequestStatus.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        "teachers.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_join_requests",
    )

    class Meta:
        verbose_name = _("Join Request")
        verbose_name_plural = _("Join Requests")
        unique_together = (("session", "user"),)
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["session", "status"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.user} → {self.session.session_code} ({self.status})"

    def clean(self):
        if self.pk and self.status != JoinRequestStatus.PENDING:
            # Optional: prevent changing status directly
            pass

    def mark_reviewed(self, teacher):
        self.reviewed_by = teacher
        self.reviewed_at = timezone.now()
        self.save(update_fields=["reviewed_by", "reviewed_at"])

