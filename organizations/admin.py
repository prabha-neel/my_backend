# Register your models here.

from django.contrib import admin
from .models import Organization, SchoolAdmin

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    # 1. Behtar display: Slug aur Type bhi dikhao
    list_display = ('name', 'org_id', 'org_type', 'is_active', 'is_verified', 'created_at')
    
    # 2. Sidebar filters: Type aur Verification status ke basis par filter
    list_filter = ('org_type', 'is_active', 'is_verified', 'created_at')
    
    # 3. Search optimization
    search_fields = ('name', 'org_id', 'registration_number', 'admin__email')
    
    # 4. Readonly fields: Taki auto-generated IDs koi manual na badal sake
    readonly_fields = ('id', 'slug', 'org_id', 'created_at', 'updated_at')
    
    # 5. Fieldsets: Admin form ko organized rakho
    fieldsets = (
        ("Basic Identity", {
            'fields': ('id', 'name', 'slug', 'org_id', 'admin')
        }),
        ("Registration Info", {
            'fields': ('org_type', 'registration_number', 'affiliation_board')
        }),
        ("Status & Verification", {
            'fields': ('is_active', 'is_verified', 'verification_date', 'verification_notes')
        }),
        ("Timestamps", {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',), # Isko default hide rakho
        }),
    )

@admin.register(SchoolAdmin)
class SchoolAdminProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'designation', 'is_active')
    list_filter = ('is_active', 'organization')
    search_fields = ('user__username', 'user__email', 'organization__name')
    list_editable = ('is_active',)
    raw_id_fields = ('user', 'organization') # Badi list mein user dhundna aasaan hoga