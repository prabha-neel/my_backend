from rest_framework import permissions

class IsStudentOwnerOrStaff(permissions.BasePermission):
    """
    1. SuperAdmin/Staff: Sab dekh sakte hain.
    2. Student: Sirf apni profile aur apna data (Results/Fees) dekh sakta hai.
    """
    def has_object_permission(self, request, view, obj):
        # Admin ko full access
        if request.user.is_staff:
            return True
        
        # Kya ye bacha khud apni profile dekh raha hai?
        # obj yahan StudentProfile ka instance hai
        return obj.user == request.user


class IsTeacherOfStudent(permissions.BasePermission):
    """
    Teacher sirf unhi bacho ko dekh sake jo uski class/session mein hain.
    """
    def has_object_permission(self, request, view, obj):
        if not hasattr(request.user, 'teacher_profile'):
            return False
            
        # Check: Kya ye teacher is student ke kisi bhi session se juda hai?
        from .models import StudentSession
        return StudentSession.objects.filter(
            student=obj, 
            teacher=request.user.teacher_profile
        ).exists()

class CanApproveParentRequest(permissions.BasePermission):
    """
    Sirf wahi student approve kar sakta hai jise request bheji gayi hai.
    """
    def has_object_permission(self, request, view, obj):
        # obj yahan StudentProfile hai jise approve kiya ja raha hai
        return obj.user == request.user