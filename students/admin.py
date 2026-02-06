from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import StudentProfile, StudentSession, StudentResult, StudentFee

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    # ─── List View ──────────────────────────────────────────────────────────
    list_display = (
        "full_name_link",
        "student_unique_id",  # Aapke views aur models mein yahi field hai
        "organization",
        "is_active_badge",
        "created_at",
    )
    list_display_links = ("full_name_link",)
    list_per_page = 25
    list_select_related = ("user", "organization")

    # Searching
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "student_unique_id",
    )

    # Filtering
    list_filter = (
        "is_active",
        "organization",
        ("created_at", admin.DateFieldListFilter),
    )

    # ─── Form Layout ────────────────────────────────────────────────────────
    fieldsets = (
        (_("Identity"), {
            "fields": (
                "user",
                "student_unique_id",
            )
        }),
        (_("Academic & Org"), {
            "fields": (
                "organization",
            )
        }),
        (_("Status & Tracking"), {
            "fields": (
                "is_active",
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",),
        }),
    )

    readonly_fields = ("student_unique_id", "created_at", "updated_at")
    raw_id_fields = ("user",)

    # ─── Custom Display Methods ──────────────────────────────────────────────
    
    @admin.display(description=_("Student Name"), ordering="user__first_name")
    def full_name_link(self, obj):
        try:
            url = reverse("admin:normal_user_normaluser_change", args=(obj.user.id,))
        except:
            url = "#"
        name = obj.user.get_full_name() or obj.user.username
        # Yahan do {} hain, ek href ke liye aur ek text ke liye
        return format_html('<a href="{}" style="font-weight: bold; color: #447e9b;">{}</a>', url, name)

    @admin.display(description=_("Status"))
    def is_active_badge(self, obj):
        if obj.is_active:
            # Yahan {} lagana zaroori hai taaki Django ko pata chale text kahan daalna hai
            return format_html('<span style="background: #28a745; color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.85em;">{}</span>', "Active")
        return format_html('<span style="background: #dc3545; color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.85em;">{}</span>', "Inactive")

    # ─── Actions ────────────────────────────────────────────────────────────
    @admin.action(description=_("Mark selected as active"))
    def make_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description=_("Mark selected as inactive"))
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)

    actions = ["make_active", "make_inactive"]

# ─── Registering Other Models ──────────────────────────────────────────────
@admin.register(StudentSession)
class StudentSessionAdmin(admin.ModelAdmin):
    list_display = ('subject', 'student', 'teacher', 'session_date')
    list_filter = ('subject', 'session_date')
    raw_id_fields = ('student', 'teacher')

@admin.register(StudentResult)
class StudentResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam_name', 'marks_obtained', 'total_marks', 'exam_date')
    list_filter = ('exam_date',)

@admin.register(StudentFee)
class StudentFeeAdmin(admin.ModelAdmin):
    list_display = ('student', 'amount', 'due_date', 'status')
    list_filter = ('status', 'due_date')