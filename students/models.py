import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

# ────────────────────────────────────────────────
# 1. Student Profile Model
# ────────────────────────────────────────────────
class StudentProfile(models.Model):
    """
    Core student model. Linked to NormalUser.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='students'
    )
    student_unique_id = models.CharField(
        max_length=20, 
        unique=True, 
        db_index=True,
        help_text="Roll number or admission number"
    )
    current_standard = models.ForeignKey(
        'students_classroom.Standard', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='enrolled_students'
    )
    is_active = models.BooleanField(default=True, db_index=True)

    # Metadata for 'explore' action
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='students/profiles/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Student Profile"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.student_unique_id})"


# ────────────────────────────────────────────────
# 2. Student Session (Teacher-Student Link)
# ────────────────────────────────────────────────
class StudentSession(models.Model):
    """
    Objective #6: Tracks sessions between teachers and students.
    """
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='sessions')
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='teacher_sessions'
    )
    subject = models.CharField(max_length=100)
    topic = models.CharField(max_length=255, blank=True)
    session_date = models.DateTimeField(db_index=True)
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='sessions_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} - {self.student.user.first_name}"


# ────────────────────────────────────────────────
# 3. Student Result (Performance Tracking)
# ────────────────────────────────────────────────
class StudentResult(models.Model):
    """
    Exam/Test results for students.
    """
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='results')
    exam_name = models.CharField(max_length=200)
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2)
    total_marks = models.DecimalField(max_digits=5, decimal_places=2)
    exam_date = models.DateField(db_index=True)
    grade = models.CharField(max_length=5, blank=True)

    class Meta:
        # 'views.py' uses order_by("-exam__date"), so we need either a ForeignKey to Exam 
        # or we use exam_date here. Let's keep it simple for now.
        ordering = ['-exam_date']

# ────────────────────────────────────────────────
# 4. Student Fee (Financial Tracking)
# ────────────────────────────────────────────────
class StudentFee(models.Model):
    """
    Fee tracking for students.
    """
    STATUS_CHOICES = (
        ('PAID', 'Paid'),
        ('PENDING', 'Pending'),
        ('OVERDUE', 'Overdue'),
    )
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='fees')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    due_date = models.DateField(db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.student.student_unique_id} - {self.amount} ({self.status})"