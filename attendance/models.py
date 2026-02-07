from django.db import models
from django.utils import timezone

class Attendance(models.Model):
    STATUS_CHOICES = (
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LEAVE', 'Leave'),
    )
    
    # Relationships
    student = models.ForeignKey('students.StudentProfile', on_delete=models.CASCADE)
    standard = models.ForeignKey('students_classroom.Standard', on_delete=models.CASCADE)
    
    # Core Fields
    # db_index=True se search fast hogi
    date = models.DateField(default=timezone.now, db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    
    # Audit Fields
    marked_by = models.ForeignKey('normal_user.NormalUser', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ek bacha, ek din, ek attendance
        unique_together = ('student', 'date')
        verbose_name_plural = "Attendance"

    def __str__(self):
        return f"{self.student.student_unique_id} - {self.date} ({self.status})"