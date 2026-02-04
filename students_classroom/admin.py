from django.contrib import admin

# Register your models here.

import csv
from django.contrib import admin, messages
from django.db.models import Count
from django.utils.html import format_html
from django.http import HttpResponse
from django.urls import reverse

from .models import (
    Standard,
    ClassroomSession,
    # Student,
    JoinRequest,
)

# =================================================
# 1. Standard Admin
# =================================================
@admin.register(Standard)
class StandardAdmin(admin.ModelAdmin):
    # 'section' bhi add kar diya taaki admin panel mein Class aur Section dono dikhein
    list_display = ('name', 'section', 'student_count', 'created_at') 
    search_fields = ('name', 'section')
    ordering = ('name',)

    def get_queryset(self, request):
        # Yahan 'enrolled_students' hi rehne dena kyunki model mein wahi hai
        return super().get_queryset(request).annotate(
            total_students_count=Count('enrolled_students', distinct=True) 
        )

    @admin.display(description="Total Students", ordering='total_students_count')
    def student_count(self, obj):
        # Yahan annotate kiya hua variable use kar rahe hain
        return obj.total_students_count


# =================================================
# 2. JoinRequest Inline (To see requests inside Session)
# =================================================
class JoinRequestInline(admin.TabularInline):
    model = JoinRequest
    extra = 0
    can_delete = False
    readonly_fields = ('user', 'status', 'created_at')
    fields = ('user', 'status', 'created_at')
    classes = ('collapse',)

    def has_add_permission(self, request, obj=None):
        return False


# =================================================
# 3. ClassroomSession Admin
# =================================================
@admin.register(ClassroomSession)
class ClassroomSessionAdmin(admin.ModelAdmin):
    list_display = (
        'session_code',
        'teacher_name',
        'target_standard',
        'seat_usage',
        'status_badge',
        'expires_at',
    )
    list_filter = (
        'status',
        'target_standard',
        ('created_at', admin.DateFieldListFilter),
    )
    search_fields = ('session_code', 'teacher__user__username', 'target_standard__name')
    readonly_fields = ('session_code', 'created_at', 'updated_at')
    inlines = (JoinRequestInline,)
    ordering = ('-created_at',)
    
    actions = ('force_close_sessions', 'sync_session_statuses', 'export_as_csv')

    # Custom Columns
    @admin.display(description="Teacher")
    def teacher_name(self, obj):
        return obj.teacher.user.get_full_name() or obj.teacher.user.username

    @admin.display(description="Seats (Used/Total)")
    def seat_usage(self, obj):
        return f"{obj.current_student_count} / {obj.student_limit}"

    @admin.display(description="Status")
    def status_badge(self, obj):
        # Using bootstrap-like colors that Django Admin supports
        colors = {
            'ACTIVE': '#28a745', # Green
            'FULL': '#ffc107',   # Yellow
            'EXPIRED': '#dc3545',# Red
            'CLOSED': '#6c757d', # Grey
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 5px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#000'),
            obj.get_status_display()
        )

    # Actions Logic
    @admin.action(description="Force close selected sessions")
    def force_close_sessions(self, request, queryset):
        for session in queryset:
            session.close() # Tumhare model ka close() method
        self.message_user(request, "Sessions closed and pending requests rejected.", messages.SUCCESS)

    @admin.action(description="Sync statuses (Check Expiry/Full)")
    def sync_session_statuses(self, request, queryset):
        for session in queryset:
            session.sync_status() # Tumhare model ka sync_status()
        self.message_user(request, "Statuses refreshed successfully.", messages.INFO)

    @admin.action(description="Export to CSV")
    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sessions.csv"'
        writer = csv.writer(response)
        writer.writerow(['Code', 'Standard', 'Teacher', 'Status', 'Expires'])
        for s in queryset:
            writer.writerow([s.session_code, s.target_standard.name, s.teacher.user.username, s.status, s.expires_at])
        return response


# =================================================
# 4. Student Admin
# =================================================
# @admin.register(Student)
# class StudentAdmin(admin.ModelAdmin):
#     list_display = ('user', 'standard', 'admitted_via_session', 'is_active', 'joined_at')
#     list_filter = ('standard', 'is_active')
#     search_fields = ('user__username', 'user__email')
#     raw_id_fields = ('user', 'admitted_via_session') # Massive optimization for large data


# =================================================
# 5. JoinRequest Admin
# =================================================
@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_code', 'status_colored', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'session__session_code')

    @admin.display(description="Session Code")
    def session_code(self, obj):
        return obj.session.session_code

    @admin.display(description="Status")
    def status_colored(self, obj):
        colors = {'PENDING': 'orange', 'ACCEPTED': 'green', 'REJECTED': 'red'}
        return format_html('<b style="color: {};">{}</b>', colors.get(obj.status, 'black'), obj.status)