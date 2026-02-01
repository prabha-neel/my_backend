#permissions.py
from rest_framework import permissions

class IsStaffOrReadOnly(permissions.BasePermission):
    """
    SuperAdmin (Staff) ko full access hai.
    Baaki sab sirf GET (List/Retrieve) kar sakte hain.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)

class IsOrganizationMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        
        profile = getattr(request.user, 'school_admin_profile', None)
        if not profile:
            return False

        # Agar hum seedha Organization object ko check kar rahe hain
        from .models import Organization
        if isinstance(obj, Organization):
            return obj == profile.organization # Object to Object comparison is safer
        
        # Agar hum SchoolAdmin ya kisi aur model ko check kar rahe hain jisme org foreign key hai
        if hasattr(obj, 'organization'):
            return obj.organization == profile.organization
            
        return False