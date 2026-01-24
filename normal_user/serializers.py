# serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.core.validators import RegexValidator
from .models import NormalUser
import re
from .models import Notification


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
            'password', 'mobile', 'gender', 'bloodgroup', 'dob', 'address'
        ]
        extra_kwargs = {
            'id': {'read_only': True},
            'username': {'required': True},
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
        # Ek hi jagah teeno unique fields check kar rahe hain (active users only)
        if NormalUser.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "This username is already taken."})
        if NormalUser.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "This email is already registered."})
        if NormalUser.objects.filter(mobile=data['mobile']).exists():
            raise serializers.ValidationError({"mobile": "This mobile number is already registered."})
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = NormalUser(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    user_name = serializers.CharField(required=True, max_length=150)
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        login_field = data.get('user_name').strip()
        password = data.get('password')

        user = None

        # 1. Username se try (case insensitive nahi, Django username case sensitive hota hai)
        user = authenticate(username=login_field, password=password)
        if user and user.is_active and not user.is_deleted:
            data['user'] = user
            return data

        # 2. Email se try (case insensitive)
        try:
            user_obj = NormalUser.objects.get(email__iexact=login_field)
            if user_obj.is_active and not user_obj.is_deleted:
                user = authenticate(username=user_obj.username, password=password)
                if user:
                    data['user'] = user
                    return data
        except NormalUser.DoesNotExist:
            pass

        # 3. Mobile se try
        try:
            user_obj = NormalUser.objects.get(mobile=login_field)
            if user_obj.is_active and not user_obj.is_deleted:
                user = authenticate(username=user_obj.username, password=password)
                if user:
                    data['user'] = user
                    return data
        except NormalUser.DoesNotExist:
            pass

        raise serializers.ValidationError("Invalid credentials. Please check your username/email/mobile or password.")


class AccountDeleteSerializer(serializers.Serializer):
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=True,
        error_messages={'blank': 'Password is required.'}
    )

    def validate_password(self, value):
        if not value or value.strip() == '':
            raise serializers.ValidationError("Password cannot be empty.")
        return value
    

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']