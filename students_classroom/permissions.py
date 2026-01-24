from rest_framework import permissions

class IsSessionTeacherOrAdmin(permissions.BasePermission):
    """
    1. SuperAdmin: Full Access.
    2. School Admin: Apne school ke kisi bhi teacher ka session manage kar sake.
    3. Teacher: Sirf apna banaya hua session manage kar sake.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # 1. SuperAdmin Check
        if user.is_staff:
            return True
        
        # 2. School Admin Check (Organization match hona chahiye)
        if hasattr(user, "school_admin_profile"):
            return obj.organization == user.school_admin_profile.organization
            
        # 3. Teacher Check (Wahi teacher jisne banaya)
        return hasattr(user, 'teacher_profile') and obj.teacher == user.teacher_profile


class CanJoinSession(permissions.BasePermission):
    """
    Objective: Sirf wo users request bhej sakein jinka abhi tak 
    na toh Student Profile hai aur na hi Teacher Profile.
    (Yani ekdam Fresh/Normal User)
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
            
        # Check: Kya ye banda pehle se Student ya Teacher toh nahi hai?
        is_already_student = hasattr(user, 'student_profile')
        is_already_teacher = hasattr(user, 'teacher_profile')
        is_already_admin = hasattr(user, 'school_admin_profile')

        # Sirf tab allow karo jab banda bilkul fresh user ho
        return not (is_already_student or is_already_teacher or is_already_admin)