#organizations app serializers.py
from rest_framework import serializers
from django.db import transaction
from django.core.validators import RegexValidator
from .models import Organization, SchoolAdmin
from normal_user.models import NormalUser
from django.db import models # Q object ke liye zaroori hai

class OrganizationSerializer(serializers.ModelSerializer):
    # --- 1. Purana Validation Logic (Regex same rakha hai) ---
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )

    # --- 2. Purane Read-only Fields (Response ke liye) ---
    admin_username = serializers.CharField(source='admin.username', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    # --- 3. Nayi Mapping (Jo tune nayi request mein maangi hai) ---
    org_name = serializers.CharField(source='name')
    org_email = serializers.EmailField(source='contact_email')
    org_mobile = serializers.CharField(source='phone_number', validators=[phone_regex], required=False, allow_blank=True)
    org_address = serializers.CharField(source='address')
    org_city = serializers.CharField(source='city', required=False, allow_blank=True)
    org_pincode = serializers.CharField(source='pincode', required=False, allow_blank=True)
    org_board = serializers.CharField(source='affiliation_board', required=False, allow_blank=True)
    
    # --- 4. Admin Creation Fields (Jo tune nayi request mein batayi) ---
    admin_name = serializers.CharField(write_only=True, required=True)
    admin_email = serializers.EmailField(write_only=True, required=True)
    admin_mobile = serializers.CharField(validators=[phone_regex], write_only=True, required=True)
    admin_password = serializers.CharField(write_only=True, required=True, min_length=8)

    class Meta:
        model = Organization
        fields = [
            'id', 'org_name', 'org_email', 'org_mobile', 'org_type', 
            'org_address', 'org_city', 'org_pincode', 'org_board', 
            'established_year', 'admin_name', 'admin_email', 
            'admin_mobile', 'admin_password', 'slug', 'org_id',
            'admin_username', 'created_by_username'
        ]
        read_only_fields = ['id', 'slug', 'org_id', 'admin_username', 'created_by_username']

    @transaction.atomic
    def create(self, validated_data):
        # 1. Sabse pehle admin ka data nikaal lo
        full_name = validated_data.pop('admin_name')
        email = validated_data.pop('admin_email')
        mobile = validated_data.pop('admin_mobile')
        password = validated_data.pop('admin_password')

        # 2. Check karo kya ye admin pehle se database mein hai?
        # Agar mobile ya email match ho gaya toh wahi user utha lega
        user = NormalUser.objects.filter(models.Q(mobile=mobile) | models.Q(email=email)).first()

        if not user:
            # 3. CASE A: Agar user NAYA hai, toh use create karo
            try:
                user = NormalUser.objects.create_user(
                    mobile=mobile,
                    email=email,
                    username=email,
                    password=password,
                    first_name=full_name,
                    dob="2000-01-01",
                    role='SCHOOL_ADMIN',
                    is_active=True
                )
            except Exception as e:
                raise serializers.ValidationError({"user_creation_error": str(e)})
        else:
            # 4. CASE B: Agar user PURANA hai, toh naya user nahi banega
            # Wahi purana 'user' object use hoga naye organization se jodne ke liye
            # Role check kar lo bas safety ke liye
            if user.role != 'SCHOOL_ADMIN':
                user.role = 'SCHOOL_ADMIN'
                user.save(update_fields=['role'])

        # 5. Final Step: Naya Organization banao aur user ko link kar do
        try:
            organization = Organization.objects.create(
                admin=user,
                **validated_data
            )
        except Exception as e:
            raise serializers.ValidationError({"org_creation_error": str(e)})

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


# 1. User ke saare fields (Admin Profile)
class SchoolAdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = NormalUser
        # Password aur sensitive flags ko chhod kar baaki sab
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email', 
            'mobile', 'role', 'is_active', 'date_joined'
        ]

# 2. Organization ke saare fields
class OrganizationDetailSerializer(serializers.ModelSerializer):
    admin_custom_id = serializers.CharField(source='admin.admin_custom_id', read_only=True)
    status_display = serializers.CharField(source='is_verified_display', read_only=True) # Ye naya!

    class Meta:
        model = Organization
        # Saare fields jo tumne models.py mein likhe hain (Explicitly)
        fields = [
            'id', 'admin_custom_id', 'status_display', 'name', 'slug', 'org_id', 'registration_number', 'org_type',
            'affiliation_board', 'logo', 'description', 'address', 'phone_number',
            'contact_email', 'website', 'established_year', 'city', 'locality',
            'pincode', 'instruction_medium', 'gender_type', 'fee_category',
            'monthly_fees_min', 'has_transport', 'has_hostel', 'has_smart_class',
            'has_library', 'has_playground', 'is_active', 'is_verified',
            'verification_date', 'created_at', 'updated_at'
        ]


    