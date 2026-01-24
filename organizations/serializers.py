from rest_framework import serializers
from django.db import transaction
from django.core.validators import RegexValidator
from .models import Organization, SchoolAdmin
from normal_user.models import NormalUser

class OrganizationSerializer(serializers.ModelSerializer):
    # Custom fields for admin creation
    admin_username = serializers.CharField(source='admin.username', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    # Industry standard mobile validation
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    admin_mobile = serializers.CharField(validators=[phone_regex], write_only=True, required=True)
    admin_password = serializers.CharField(write_only=True, required=True, min_length=8)

    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'org_id', 'registration_number', 
            'org_type', 'affiliation_board', 'admin', 'admin_username',
            'admin_mobile', 'admin_password',
            'address', 'is_active', 'is_verified', 'created_at',
            'created_by', 'created_by_username'
        ]
        read_only_fields = ['id', 'slug', 'org_id', 'admin', 'created_at', 'created_by']

    def validate_admin_mobile(self, value):
        """Check if a user with this mobile already exists to avoid conflicts."""
        if NormalUser.objects.filter(mobile=value).exists():
            raise serializers.ValidationError("A user with this mobile number already exists.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        # 1. Extract admin credentials
        mobile = validated_data.pop('admin_mobile')
        password = validated_data.pop('admin_password')
        request = self.context.get('request')

        # 2. Create NormalUser (School Admin Account)
        # Industry practice: Use create_user to handle password hashing automatically
        user = NormalUser.objects.create_user(
            mobile=mobile,
            username=mobile, # or any logic for username
            password=password,
            is_active=True
            # role='ORG_ADMIN' # Add this if your NormalUser model has a role field
        )

        # 3. Create Organization & Link Admin
        # 'created_by' will be the Super Admin who is currently logged in
        organization = Organization.objects.create(
            admin=user,
            **validated_data
        )

        # 4. Create SchoolAdmin Profile
        # Linking the user and organization in your profile model
        SchoolAdmin.objects.create(
            user=user,
            organization=organization,
            is_active=True
        )

        return organization
    
class SchoolAdminProfileSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = SchoolAdmin
        fields = [
            'id', 'user', 'user_full_name', 'user_email', 
            'organization', 'organization_name', 
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']