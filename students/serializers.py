from rest_framework import serializers
from .models import StudentProfile, StudentSession, StudentResult, StudentFee
from django.contrib.auth import get_user_model

User = get_user_model()

# ────────────────────────────────────────────────
# 1. Minimal Serializer (Search & Explore ke liye)
# ────────────────────────────────────────────────
class StudentMinimalSerializer(serializers.ModelSerializer):
    """
    Objective #4: Parent jab search kare toh sirf basic info dikhe.
    """
    full_name = serializers.SerializerMethodField()
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "student_unique_id",
            "full_name",
            "organization",
            "organization_name",
        ]

    def get_full_name(self, obj):
        # Professional null check agar user linked na ho
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username
        return "Unknown Student"


# ────────────────────────────────────────────────
# 2. Detailed Profile Serializer
# ────────────────────────────────────────────────
class StudentProfileSerializer(serializers.ModelSerializer):
    """
    Detailed view for Admins, Teachers, and the Student themselves.
    """
    full_name = serializers.SerializerMethodField()
    mobile = serializers.CharField(source='user.mobile', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            "id", "student_unique_id", "full_name", "mobile", "email",
            "organization", "current_standard", "is_active", "created_at"
        ]
        read_only_fields = ["student_unique_id", "created_at"]

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()


# ────────────────────────────────────────────────
# 3. Session Serializer (Point #6, #7, #8)
# ────────────────────────────────────────────────
class StudentSessionSerializer(serializers.ModelSerializer):
    """
    Teacher/Admin jo sessions create karte hain.
    """
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = StudentSession
        fields = [
            "id", "session_code", "title", "student_limit", 
            "expires_at", "status", "created_by_name"
        ]
        read_only_fields = ["session_code", "status"]


# ────────────────────────────────────────────────
# 4. Academic & Finance Serializers (Point #4)
# ────────────────────────────────────────────────
class StudentResultSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    exam_name = serializers.CharField(source='exam.title', read_only=True)

    class Meta:
        model = StudentResult
        fields = ["id", "exam_name", "subject_name", "marks_obtained", "total_marks", "grade", "remarks"]

class StudentFeeSerializer(serializers.ModelSerializer):
    fee_type_display = serializers.CharField(source='fee_type.name', read_only=True)

    class Meta:
        model = StudentFee
        fields = ["id", "fee_type_display", "amount", "due_date", "status", "paid_at"]