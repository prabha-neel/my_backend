from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator


class Teacher(models.Model):
    """
    Teacher profile model supporting both independent tutors and school-affiliated teachers.
    Designed for hybrid edtech platforms (school ERP + freelance tutoring marketplace).
    """
    # ── Identity & Core ────────────────────────────────────────────────────────
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Unique ID")
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        verbose_name=_("Associated User")
    )

    # ── Professional Details ───────────────────────────────────────────────────
    bio = models.TextField(
        max_length=2000,
        blank=True,
        verbose_name=_("Professional Bio")
    )
    qualifications = models.TextField(
        verbose_name=_("Qualifications & Certifications")
    )
    experience_years = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0.0,
        validators=[MinValueValidator(0.0)],
        verbose_name=_("Years of Experience")
    )

    # ── Expertise (flexible & queryable) ───────────────────────────────────────
    subject_expertise = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Subject Expertise"),
        help_text=_("Example: {'primary': 'Mathematics', 'secondary': ['Physics', 'Chemistry'], 'levels': ['9-10', '11-12'], 'boards': ['CBSE', 'ICSE']}")
    )

    languages_spoken = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Languages Spoken"),
        help_text=_("List like ['English', 'Hindi', 'Punjabi']")
    )

    # ── Affiliation ────────────────────────────────────────────────────────────
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teachers',
        verbose_name=_("Affiliated School/Organization")
    )

    # ── Verification & Compliance (critical for production) ────────────────────
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_("Verified by Platform")
    )
    verification_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Verification Date")
    )
    verification_notes = models.TextField(
        blank=True,
        verbose_name=_("Verification Internal Notes")
    )

    # ── Professional / Marketplace Fields (freelance tutors ke liye must-have) ─
    profile_picture = models.ImageField(
        upload_to='teacher_profiles/%Y/%m/',
        blank=True,
        null=True,
        verbose_name=_("Profile Picture")
    )
    hourly_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(100.00)],
        verbose_name=_("Hourly Rate (INR)")
    )
    preferred_mode = models.CharField(
        max_length=20,
        choices=[
            ('online', _("Online")),
            ('offline', _("Offline")),
            ('hybrid', _("Both")),
        ],
        default='online',
        verbose_name=_("Preferred Teaching Mode")
    )
    service_areas = models.JSONField(  # cities or pincodes
        default=list,
        blank=True,
        verbose_name=_("Service Areas (for offline)"),
        help_text=_("e.g. ['Delhi', 'Noida', 'Gurgaon'] or pincodes")
    )

    # ── Status & Moderation ────────────────────────────────────────────────────
    is_active_teacher = models.BooleanField(
        default=True,
        verbose_name=_("Active on Platform")
    )
    rejection_reason = models.TextField(
        blank=True,
        verbose_name=_("Rejection Reason (if not verified)")
    )

    # ── Audit Trail ────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Teacher")
        verbose_name_plural = _("Teachers")
        ordering = ['-created_at']
        indexes = [
            # 'id' par index banane ki zaroorat nahi hoti, Django auto banata hai
            models.Index(fields=['organization']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['is_active_teacher']),
            # 'user__is_active' yahan se hata diya gaya hai
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(experience_years__gte=0),
                name='experience_non_negative'
            ),
        ]

    def __str__(self):
        name = self.user.get_full_name() or self.user.username
        status = _("Independent Tutor") if not self.organization else _("School Teacher")
        verified = _("✓ Verified") if self.is_verified else _("Pending")
        return f"{name} - {status} ({verified})"

    @property
    def is_independent(self) -> bool:
        return self.organization is None

    @property
    def full_name(self) -> str:
        return self.user.get_full_name() or self.user.username

    def get_expertise_summary(self) -> str:
        """Helper for frontend display or search snippets"""
        if not self.subject_expertise:
            return _("Not specified")
        primary = self.subject_expertise.get('primary', '')
        others = ', '.join(self.subject_expertise.get('secondary', []))
        return f"{primary}{(' + ' + others) if others else ''}"

    # Future: add clean() method for validation if needed