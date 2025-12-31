# models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
import time


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        return self.update(is_deleted=True, deleted_at=timezone.now(), is_active=False)

    def hard_delete(self):
        return super().delete()

    def active(self):
        return self.filter(is_deleted=False, is_active=True)

    def deleted(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).active()


class AllObjectsManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class NormalUser(AbstractUser):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )

    BLOOD_GROUP_CHOICES = (
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    )

    ROLE_CHOICES = [
        ('NORMAL', 'Normal'),
        ('STUDENT', 'Student'),
        ('TEACHER', 'Teacher'),
        ('PARENT', 'Parent'),
    ]

    # Profile Fields
    mobile = models.CharField(max_length=15, unique=True, db_index=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    bloodgroup = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES, blank=True, null=True)
    dob = models.DateField("Date of Birth", blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    email = models.EmailField(unique=True, db_index=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='NORMAL')

    # Soft Delete & Audit
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_users',
    )

    # Managers
    objects = BaseUserManager()           # Default Django auth ke liye
    active_objects = SoftDeleteManager()  # Sirf active users
    all_objects = AllObjectsManager()     # Sab including deleted

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['mobile']),
            models.Index(fields=['role']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['is_active']),
            models.Index(fields=['deleted_at']),
        ]

    def __str__(self):
        return self.get_full_name() or self.username or self.email or f"User {self.id}"

    def soft_delete(self, deleted_by=None):
        """Safe soft delete – all unique fields ko modify kar deta hai"""
        self.is_active = False
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by

        timestamp = int(time.time())

        if self.email:
            self.email = f"deleted_{self.id}_{timestamp}@deleted.example.com"
        if self.username:
            self.username = f"deleted_user_{self.id}_{timestamp}"
        if self.mobile:  # ← YE ADD KIYA – critical fix!
            self.mobile = f"deleted_mobile_{self.id}_{timestamp}"

        self.save(update_fields=[
            'is_active', 'is_deleted', 'deleted_at',
            'deleted_by', 'email', 'username', 'mobile'
        ])

    def restore(self, original_email=None, original_username=None, original_mobile=None):
        """Restore soft-deleted user with original values"""
        self.is_active = True
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None

        if original_email:
            self.email = original_email
        if original_username:
            self.username = original_username
        if original_mobile:
            self.mobile = original_mobile

        self.save(update_fields=[
            'is_active', 'is_deleted', 'deleted_at',
            'deleted_by', 'email', 'username', 'mobile'
        ])

    def permanent_delete(self):
        """Admin only – real delete"""
        super().delete()