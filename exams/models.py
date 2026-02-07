import uuid
from django.db import models
from django.conf import settings
from students_classroom.models import Standard
from organizations.models import Organization

class Exam(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'), 
        ('PUBLISHED', 'Published'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed')
    ]

    # --- HIDDEN/ESSENTIAL FIELDS ---
    # UUID use karne se URL mein ID guess karna namumkin ho jata hai (Security)
    external_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="exams")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="exams_created")
    created_at = models.DateTimeField(auto_now_add=True) # Kab bana
    updated_at = models.DateTimeField(auto_now=True)     # Kab last change hua
    is_active = models.BooleanField(default=True)       # Soft delete ke liye
    
    # --- USER DATA ---
    target_standard = models.ForeignKey(Standard, on_delete=models.CASCADE)
    exam_title = models.CharField(max_length=200)
    academic_year = models.CharField(max_length=20, help_text="e.g. 2025-26") # ✅ help_text sahi hai
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    def __str__(self):
        return f"{self.exam_title} - {self.target_standard.name}"

class ExamSubject(models.Model):
    exam = models.ForeignKey(Exam, related_name='subjects', on_delete=models.CASCADE)
    subject_name = models.CharField(max_length=100)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # --- ADDITIONAL ESSENTIALS ---
    room_no = models.CharField(max_length=50, blank=True, null=True)
    max_marks = models.PositiveIntegerField(default=100)
    passing_marks = models.PositiveIntegerField(default=33)
    instruction = models.TextField(blank=True, null=True) # Har subject ke liye alag instruction (e.g. "Bring Calculator")

    class Meta:
        ordering = ['date', 'start_time']