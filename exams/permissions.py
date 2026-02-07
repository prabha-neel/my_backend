from rest_framework import permissions

class IsAdminOrTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        # 1. Check karo user logged in hai ya nahi
        if not request.user or not request.user.is_authenticated:
            return False

        # 2. Agar user Super Admin hai, toh seedha permission de do
        if request.user.role == 'SUPER_ADMIN':
            return True

        # 3. School Admin aur Teacher ke liye check
        if request.user.role in ['SCHOOL_ADMIN', 'TEACHER']:
            # Profile check karo (Kyunki NormalUser mein organization nahi hai)
            has_profile = request.user.school_admin_profile.filter(is_active=True).exists()
            return has_profile

        # 4. Students sirf GET (View) kar sakte hain, POST nahi
        if request.user.role == 'STUDENT':
            return request.method in permissions.SAFE_METHODS

        return False