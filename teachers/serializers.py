from rest_framework import serializers
from .models import Teacher

class TeacherPublicSerializer(serializers.ModelSerializer):
    """Objective #4: Normal users search karein tab ke liye"""
    full_name = serializers.CharField(read_only=True)
    expertise_summary = serializers.CharField(source='get_expertise_summary', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = Teacher
        fields = [
            'id', 'full_name', 'profile_picture', 'bio', 
            'expertise_summary', 'experience_years', 'hourly_rate', 
            'preferred_mode', 'is_verified', 'organization_name'
        ]

class TeacherProfileSerializer(serializers.ModelSerializer):
    """Objective #9: Teacher apni details manage karega tab ke liye"""
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Teacher
        fields = '__all__'
        read_only_fields = ['id', 'user', 'is_verified', 'organization', 'created_at']