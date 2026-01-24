import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

class ParentProfile(models.Model):
    # ─── IDENTITY ───────────────────────────────────────────────────────────────
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="parent_profile",
        verbose_name=_("User Account"),
    )

    # ─── RELATIONSHIPS ──────────────────────────────────────────────────────────
    # ManyToMany: Ek parent ke multiple bache ho sakte hain
    students = models.ManyToManyField(
        "students.StudentProfile",
        related_name="parents",
        blank=True,
        verbose_name=_("Children"),
    )

    # ─── CONTACT & INFO ─────────────────────────────────────────────────────────
    phone_number = PhoneNumberField(
        _("Phone Number"),
        blank=True,
        null=True,
        unique=True,
        help_text=_("International format use karein, e.g. +919876543210"),
    )

    RELATION_CHOICES = [
        ("FATHER", _("Father")),
        ("MOTHER", _("Mother")),
        ("GUARDIAN", _("Legal Guardian")),
        ("OTHER", _("Other")),
    ]

    relation = models.CharField(
        _("Relation to Child"),
        max_length=20,
        choices=RELATION_CHOICES,
        default="FATHER",
    )

    address = models.TextField(
        _("Home Address"),
        blank=True,
    )

    # ─── STATUS & TRACKING ──────────────────────────────────────────────────────
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Parent")
        verbose_name_plural = _("Parents")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone_number"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        name = self.user.get_full_name() or self.user.username
        return f"Parent: {name} ({self.get_relation_display()})"

    @property
    def children_list(self):
        """Sare bachon ke naam ek string mein dikhane ke liye"""
        if not self.pk:
            return ""
        return ", ".join([str(s) for s in self.students.all()])
    
# parents/models.py ke end mein ye add karein:

class ParentStudentLink(models.Model):
    """
    Objective #11: Approval flow ke liye link model.
    Jab parent request bhejega, toh student use approve ya reject kar sakega.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')

    parent = models.ForeignKey(
        ParentProfile, 
        on_delete=models.CASCADE, 
        related_name="student_links"
    )
    student = models.ForeignKey(
        "students.StudentProfile", 
        on_delete=models.CASCADE, 
        related_name="parent_links"
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING,
        verbose_name=_("Link Status")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Parent Student Link")
        verbose_name_plural = _("Parent Student Links")
        unique_together = ('parent', 'student') # Taki duplicate link na bane