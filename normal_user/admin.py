from django.contrib import admin
from .models import NormalUser, Notification

# Register your models here.

admin.site.register(NormalUser)
admin.site.register(Notification)