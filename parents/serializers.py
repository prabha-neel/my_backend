from rest_framework import serializers
from .models import ParentProfile, ParentStudentLink
from django.contrib.auth import get_user_model
User = get_user_model()
from students.serializers import StudentMinimalSerializer

# --- 1. Profile Serializer (Normal User -> Parent conversion ke liye) ---
class ParentProfileDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    mobile = serializers.CharField(source='user.mobile', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = ParentProfile
        fields = [
            "id", "user", "full_name", "mobile", "email",
            "is_active", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "user", "is_active", "created_at", "updated_at"]

    def validate(self, data):
        request = self.context.get('request')
        if request and request.method == "POST":
            if ParentProfile.objects.filter(user=request.user).exists():
                raise serializers.ValidationError("Parent profile already exists for this user.")
        return data

# --- 2. Handshake Serializer (Student se link hone ke liye) ---
class ParentStudentLinkSerializer(serializers.ModelSerializer):
    # Bache ki details nested dikhayenge
    student = StudentMinimalSerializer(read_only=True)
    # Status readable banane ke liye (e.g. "Pending")
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ParentStudentLink
        fields = [
            "id", "student", "status", "status_display", 
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "student", "status"]