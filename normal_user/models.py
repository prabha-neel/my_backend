# normaluser ki models.py
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone
import time
from django.conf import settings


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

    class Roles(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        SCHOOL_ADMIN = 'SCHOOL_ADMIN', 'School Admin'
        TEACHER = 'TEACHER', 'Teacher'
        STUDENT = 'STUDENT', 'Student'
        PARENT = 'PARENT', 'Parent'
        GUEST = 'GUEST', 'Independent User'

    # Profile Fields
    mobile = models.CharField(max_length=15, unique=False, db_index=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    bloodgroup = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES, blank=True, null=True)
    dob = models.DateField("Date of Birth", blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.GUEST)
    
    admin_custom_id = models.CharField(
        max_length=50, 
        unique=True, 
        null=True, 
        blank=True, 
        editable=False
    )

    @property
    def is_school_admin(self):
        return self.role == self.Roles.SCHOOL_ADMIN

    @property
    def is_teacher(self):
        return self.role == self.Roles.TEACHER

    @property
    def is_student(self):
        return self.role == self.Roles.STUDENT

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
    objects = UserManager()                 # Default Django auth ke liye
    active_objects = SoftDeleteManager()    # Sirf active users
    all_objects = AllObjectsManager()       # Sab including deleted

    REQUIRED_FIELDS = ['email', 'mobile', 'dob']
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
        indexes = [
            # Email aur Mobile par unique/db_index pehle se hai, 
            # yahan dobara likhne ki zaroorat nahi hai.
            models.Index(fields=['role']),
            models.Index(fields=['is_deleted', 'is_active']), # Composite index (Faster)
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
        if self.admin_custom_id:
            self.admin_custom_id = f"DEL-{self.admin_custom_id}-{timestamp}"

        self.save(update_fields=[
            'is_active', 'is_deleted', 'deleted_at',
            'deleted_by', 'email', 'username', 'mobile', 'admin_custom_id'
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



class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at'] # Naye notification sabse upar dikhenge

    def __str__(self):
        return f"{self.recipient.username} - {self.title}"
    

    # signup hone par notification ke liye ye functioin hai
def create_notification(user, title, message, n_type='info'):
    return Notification.objects.create(
        recipient=user,
        title=title,
        message=message,
        notification_type=n_type
    )