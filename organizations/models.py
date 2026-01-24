from django.db import models

# Create your models here.

from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.urls import reverse
from django.utils import timezone  # Correct way to get current year
import uuid

class Organization(models.Model):
    """
    Professional model for Schools, Coaching Centers, Colleges, Academies or any Educational Institution/Body.
    """
    # ── Identity & URL Safety ──────────────────────────────────────────────────
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("Unique ID")
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_("Organization Name")
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        verbose_name=_("Slug (URL-friendly)"),
        help_text=_("Auto-generated from name; used in URLs like /org/my-school/")
    )

    # ── Official & Business Identifiers ────────────────────────────────────────
    org_id = models.CharField(
        max_length=50,
        unique=True,
        blank=True, # Ab ye blank ho sakta hai kyunki hum auto-generate kar rahe hain
        verbose_name=_("Official Organization ID"),
        help_text=_("e.g. SCH-DEL-2026-001")
    )
    registration_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Registration / Affiliation Number")
    )

    # ── Type & Classification ──────────────────────────────────────────────────
    org_type = models.CharField(
        max_length=50,
        choices=[
            ('school', _("School")),
            ('coaching', _("Coaching / Tuition Center")),
            ('college', _("College / University")),
            ('academy', _("Academy / Training Institute")),
            ('online_platform', _("Online Education Platform")),
            ('other', _("Other")),
        ],
        default='school',
        verbose_name=_("Organization Type")
    )
    affiliation_board = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Affiliation Board / Curriculum")
    )

    # ── Ownership & Access Control ─────────────────────────────────────────────
    admin = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_organization',
        verbose_name=_("Organization Admin / Owner")
    )

    # ── Profile & Contact Details ──────────────────────────────────────────────
    logo = models.ImageField(
        upload_to='org_logos/%Y/%m/',
        null=True,
        blank=True,
        verbose_name=_("Logo")
    )
    description = models.TextField(blank=True, verbose_name=_("About / Description"))
    address = models.TextField(blank=True, verbose_name=_("Full Address"))
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', _("Enter a valid phone number."))],
        verbose_name=_("Contact Phone")
    )
    contact_email = models.EmailField(blank=True, verbose_name=_("Official Contact Email"))
    website = models.URLField(blank=True, verbose_name=_("Website"))
    established_year = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Established Year"))
    # ── Location & Searchability (Area-wise Filter) ───────────────────────────
    city = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name=_("City"),
        help_text=_("e.g. Agra, Delhi, Mumbai")
    )
    locality = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name=_("Locality / Area"),
        help_text=_("e.g. Sanjay Place, Civil Lines")
    )
    pincode = models.CharField(
        max_length=10, 
        blank=True, 
        null=True, 
        verbose_name=_("Pincode")
    )

    # ── Academic & Classification (Quality Filter) ───────────────────────────
    # Note: affiliation_board field pehle se hai, hum choices add kar sakte hain
    MEDIUM_CHOICES = [
        ('english', _('English')),
        ('hindi', _('Hindi')),
        ('bilingual', _('Bilingual/Both')),
    ]
    instruction_medium = models.CharField(
        max_length=20, 
        choices=MEDIUM_CHOICES, 
        default='english',
        verbose_name=_("Medium of Instruction")
    )
    
    gender_type = models.CharField(
        max_length=20,
        choices=[('coed', 'Co-Ed'), ('boys', 'Boys Only'), ('girls', 'Girls Only')],
        default='coed',
        verbose_name=_("Gender Type")
    )

    # ── Budget & Pricing (Money-wise Filter) ──────────────────────────────────
    FEE_CATEGORY_CHOICES = [
        ('budget', _('Budget Friendly')),
        ('mid_range', _('Mid-Range')),
        ('premium', _('Premium / High-End')),
    ]
    fee_category = models.CharField(
        max_length=20, 
        choices=FEE_CATEGORY_CHOICES, 
        null=True, 
        blank=True,
        verbose_name=_("Fee Category")
    )
    # Filter ke liye min/max fees (Optional but good for range filter)
    monthly_fees_min = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name=_("Approx Min Monthly Fee")
    )

    # ── Amenities & Facilities (Feature Filter) ───────────────────────────────
    has_transport = models.BooleanField(default=False, verbose_name=_("Transport Facility"))
    has_hostel = models.BooleanField(default=False, verbose_name=_("Hostel Facility"))
    has_smart_class = models.BooleanField(default=False, verbose_name=_("Smart Classes"))
    has_library = models.BooleanField(default=False, verbose_name=_("Library"))
    has_playground = models.BooleanField(default=False, verbose_name=_("Playground"))

    # ── Status & Moderation ────────────────────────────────────────────────────
    is_active = models.BooleanField(default=True, verbose_name=_("Active on Platform"))
    is_verified = models.BooleanField(default=False, verbose_name=_("Verified by Platform"))
    verification_date = models.DateTimeField(null=True, blank=True, verbose_name=_("Verification Date"))
    verification_notes = models.TextField(blank=True, verbose_name=_("Internal Verification Notes"))

    # ── Audit Trail ────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="created_organizations",
        verbose_name=_("Created By (Super-Admin)")
    )

    class Meta:
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['org_id']),
            models.Index(fields=['org_type']),
        ]

    def __str__(self):
        return f"{self.name} ({self.org_id or _('No ID')})"

    def save(self, *args, **kwargs):
        # 1. Slug Logic (Handled before saving)
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Organization.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # 2. Org ID Generation (Using timezone to avoid 'NoneType' error with created_at)
        if not self.org_id:
            current_year = timezone.now().year
            # Prefix logic
            prefix_map = {
                'school': 'SCH',
                'coaching': 'COACH',
                'college': 'COLL',
                'academy': 'ACAD',
            }
            prefix = prefix_map.get(self.org_type, 'ORG')
            
            # Generating a short unique suffix
            unique_suffix = uuid.uuid4().hex[:6].upper()
            self.org_id = f"{prefix}-{current_year}-{unique_suffix}"

        super().save(*args, **kwargs)

    @property
    def is_verified_display(self):
        return _("Yes") if self.is_verified else _("Pending")
    

# organizations/models.py
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class SchoolAdmin(models.Model):
    """
    School/Branch level administrator (Principal, Owner, Vice-Principal, Admin-in-charge, etc.)
    
    Supports:
    - Multi-school chains (one user can administer multiple schools)
    - Granular permissions per school
    - Audit trail basics
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="school_admin_profile",
        verbose_name=_("User"),
    )

    organization = models.ForeignKey(
        "Organization",
        on_delete=models.CASCADE,
        related_name="school_admins",
        verbose_name=_("School / Branch"),
    )

    designation = models.CharField(
        _("Designation"),
        max_length=100,
        default="Principal/Owner",
        help_text=_("e.g. Principal, Owner, Vice Principal, Administrator, Academic Head"),
    )

    # Core feature flags – simple but powerful for most school SaaS
    is_active = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("If unchecked, this admin loses access without deleting the record"),
    )

    can_modify_settings = models.BooleanField(
        _("Can modify school settings"),
        default=True,
        help_text=_("School name, address, logo, session/year, timetable structure etc."),
    )

    # Optional – very common in school management apps (you can remove if not needed)
    can_manage_staff = models.BooleanField(
        _("Can manage teachers & non-teaching staff"),
        default=True,
    )

    can_manage_students = models.BooleanField(
        _("Can manage students & admissions"),
        default=True,
    )

    can_view_finances = models.BooleanField(
        _("Can view fee & financial data"),
        default=False,
        help_text=_("Usually restricted to Owner / Accountant level"),
    )

    # Audit trail (very useful in multi-admin setups)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Last updated"), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_school_admins",
        verbose_name=_("Created by"),
    )

    class Meta:
        verbose_name = _("School Admin")
        verbose_name_plural = _("School Admins")

        # Prevent duplicate assignment of same user to same school
        unique_together = [["user", "organization"]]

        # Common query optimization
        indexes = [
            models.Index(fields=["user", "organization"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["organization", "is_active"]),
        ]

        # Useful for permission checks in views / DRF
        permissions = [
            ("can_change_school_core_settings", "Can change core school configuration"),
            ("can_manage_fee_structure", "Can create/edit fee heads & structures"),
            ("can_approve_financial_transactions", "Can approve fee receipts/refunds"),
            ("can_generate_admin_reports", "Can generate school-wide reports"),
        ]

    def __str__(self):
        name = self.user.get_full_name() or self.user.username
        return f"{name} • {self.designation} • {self.organization}"

    @property
    def full_name(self) -> str:
        """Convenience property for templates/serializers"""
        return self.user.get_full_name() or self.user.username

    def save(self, *args, **kwargs):
        # You can add logic here later (e.g. set created_by from request in view)
        super().save(*args, **kwargs)