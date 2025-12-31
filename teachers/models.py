from django.db import models
from django.conf import settings


# Create your models here.

class Teacher(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    preferred_subject = models.CharField(max_length=50)
    qualifications = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.user.username} - {self.preferred_subject}"