from rest_framework import permissions

class IsTeacherOwnerOrSchoolAdmin(permissions.BasePermission):
    """
    1. Teacher sirf apni profile update kare.
    2. School Admin apne affiliated teachers ko view/manage kar sake.
    3. Normal users sirf READ kar sakein.
    """
    def has_object_permission(self, request, view, obj):
        # Sabke liye viewing allowed hai (Objective #4)
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Edit authority
        is_owner = obj.user == request.user
        is_his_school_admin = (
            hasattr(request.user, 'school_admin_profile') and 
            request.user.school_admin_profile.organization == obj.organization
        )
        return is_owner or is_his_school_admin or request.user.is_staff