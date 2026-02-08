from django.db import models
from django.utils import timezone
from django.conf import settings

class Attendance(models.Model):
    STATUS_CHOICES = (
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LEAVE', 'Leave'),
    )

    # Kis bache ki attendance hai
    student = models.ForeignKey(
        'students.StudentProfile', 
        on_delete=models.CASCADE, 
        related_name='attendance_records'
    )
    
    # Kis class/standard ki attendance hai
    standard = models.ForeignKey(
        'students_classroom.Standard', 
        on_delete=models.CASCADE,
        related_name='standard_attendance'
    )
    
    # Kis date ki attendance hai (db_index se search fast hogi)
    date = models.DateField(default=timezone.now, db_index=True)
    
    # Status kya hai (P/A/L)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    
    # Haziri kisne lagayi (Teacher ya Admin)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # Kab bani aur kab update hui
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # 🚩 Sabse important: Ek student ki ek date par sirf ek entry ho sakti hai
        unique_together = ('student', 'date')
        verbose_name_plural = "Attendance"
        ordering = ['-date', 'student']

    def __str__(self):
        return f"{self.student.student_unique_id} - {self.date} ({self.status})"