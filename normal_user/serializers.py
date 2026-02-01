# serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.core.validators import RegexValidator
from .models import NormalUser
import re
import uuid
from .models import Notification
import random
import string


mobile_regex = RegexValidator(
    regex=r'^[6-9]\d{9}$',
    message="Enter a valid 10-digit Indian mobile number starting with 6-9."
)


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    mobile = serializers.CharField(validators=[mobile_regex], max_length=10)
    dob = serializers.DateField(required=False, allow_null=True, input_formats=['%Y-%m-%d', '%d-%m-%Y'])

    class Meta:
        model = NormalUser
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email',
            'password', 'mobile', 'gender', 'bloodgroup', 'dob', 'address', 'role', 
            'admin_custom_id'
        ]
        read_only_fields = ['role', 'admin_custom_id']
        extra_kwargs = {
            'id': {'read_only': True},
            'username': {'required': False},
            'email': {'required': True},
            'first_name': {'required': True},
            'mobile': {'required': True},
            'password': {'required': True},
        }

    def validate_password(self, value):
        pattern = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$')
        if not pattern.match(value):
            raise serializers.ValidationError(
                "Password must contain at least 1 uppercase, 1 lowercase, 1 number, and 1 special character (@$!%*?&)."
            )
        return value

    def validate(self, data):
        # 1. Email unique check (Zaroori hai)
        if NormalUser.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "This email is already registered."})

        # 2. AUTO-USERNAME GENERATION 🚀
        import uuid
        first_name = data.get('first_name', 'user').lower().replace(" ", "")
        mobile = data.get('mobile', '0000')
        
        # Unique username dhundne tak loop chalega (Extra Safety)
        while True:
            unique_suffix = uuid.uuid4().hex[:4]
            generated_username = f"{first_name}_{mobile[-4:]}_{unique_suffix}"
            if not NormalUser.objects.filter(username=generated_username).exists():
                data['username'] = generated_username
                break

        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        # create_user password hashing aur user creation dono handle kar lega
        user = NormalUser.objects.create_user(password=password, **validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    user_name = serializers.CharField(required=True, max_length=150)
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        login_field = data.get('user_name').strip()
        password = data.get('password')
        request = self.context.get('request')

        # 1. Single Call to Backend 🚀
        # Ye backend automatically Email, Username, ya Mobile handle kar lega
        user = authenticate(request=request, username=login_field, password=password)

        # 2. Case: Success (Unique User Mil Gaya)
        if user:
            if not user.is_active or user.is_deleted:
                raise serializers.ValidationError("This account is inactive or deleted.")
            data['user'] = user
            return data

        # 3. Case: Multiple Accounts (Mobile Login with shared password)
        # Agar authenticate None laya par request mein list hai, toh ye true hoga
        if hasattr(request, 'multiple_accounts'):
            data['user'] = None  # View handles the 'SELECT_ACCOUNT' logic
            return data

        # 4. Case: Fail (Galat Password ya No User Found)
        raise serializers.ValidationError("Invalid credentials. Please check your username/email/mobile or password.")
    

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']


class SchoolAdminUserSerializer(serializers.ModelSerializer):
    # Isse admin ko apne linked schools ki list dikhegi
    managed_schools = serializers.SerializerMethodField()

    class Meta:
        model = NormalUser
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email', 
            'mobile', 'role', 'admin_custom_id', 'managed_schools'
        ]

    def get_managed_schools(self, obj):
        # User se linked saari SchoolAdmin profiles se school ka data nikalna
        profiles = obj.school_admin_profile.all() 
        return [
            {
                "id": p.organization.id,
                "name": p.organization.name,
                "org_id": p.organization.org_id,
                "designation": p.designation,
                "is_active": p.is_active
            } for p in profiles
        ]

class NormalUserSignupSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='first_name', required=True)
    password = serializers.CharField(write_only=True, min_length=8)
    
    mobile = serializers.CharField(
        max_length=10, 
        validators=[RegexValidator(
            regex=r'^[6-9]\d{9}$',
            message="Mobile number must be 10 digits and start with 6-9."
        )]
    )

    class Meta:
        model = NormalUser
        fields = ['name', 'dob', 'gender', 'email', 'mobile', 'password']

    def validate_email(self, value):
        if NormalUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value.lower()

    # NOTE: Yahan se unique check hata diya hai taaki multi-user allow ho
    def validate_mobile(self, value):
        return value

    def validate_password(self, value):
        pattern = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$')
        if not pattern.match(value):
            raise serializers.ValidationError(
                "Password must have 1 uppercase, 1 lowercase, 1 number, and 1 special character."
            )
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        email = validated_data.pop('email')
        first_name = validated_data.pop('first_name', '')
        mobile = validated_data.get('mobile', '')

        # --- USERNAME GENERATION LOGIC ---
        # 1. Name ke pehle 3 letters (Upper case)
        name_part = first_name[:3].upper() if first_name else "USR"
        
        # 2. Mobile ke last 4 digits
        mobile_part = mobile[-4:] if len(mobile) >= 4 else "0000"
        
        # 3. 4 alphanumeric characters ki key
        key_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        
        # Final Unique Username (e.g., VIJ1022A1B2)
        generated_username = f"{name_part}{mobile_part}{key_part}"
        # ---------------------------------

        user = NormalUser.objects.create_user(
            username=generated_username, # <--- Ab username email nahi, tera formula hai
            email=email,
            password=password,
            first_name=first_name,
            **validated_data
        )
        return user
    
class AccountDeleteSerializer(serializers.Serializer):
    password = serializers.CharField(
        required=True, 
        write_only=True, 
        style={'input_type': 'password'}
    )