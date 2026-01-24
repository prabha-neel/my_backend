from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from .models import Standard, ClassroomSession, JoinRequest
from rest_framework.validators import UniqueTogetherValidator

# ✅ Correctly importing Student from the 'students' app
from students.models import StudentProfile

# ────────────────────────────────────────────────
# 1. Standard Serializers
# ────────────────────────────────────────────────

class StandardListSerializer(serializers.ModelSerializer):
    # 🎯 1. Organization field ko yahan add karein (HiddenField)
    # Isse validator ko 'organization' mil jayegi par frontend ko nahi dikhegi
    organization = serializers.HiddenField(default=None)
    teacher_name = serializers.ReadOnlyField(source='class_teacher.user.get_full_name')

    class Meta:
        model = Standard
        fields = ("id", "name", "description", "organization","class_teacher","teacher_name")
        read_only_fields = ("id","teacher_name")

        # 🎯 Ye validator 500 Error ki jagah "Class already exists" ka message dega
        validators = [
            UniqueTogetherValidator(
                queryset=Standard.objects.all(),
                fields=['organization', 'name'],
                message="Bhai, ye class is school mein pehle se bani hui hai!"
            )
        ]

    def validate_organization(self, value):
        user = self.context['request'].user
        if hasattr(user, 'school_admin_profile'):
            # Admin ki organization auto-select ho jayegi
            return user.school_admin_profile.organization
        raise serializers.ValidationError("Sirf School Admin hi class bana sakte hain!")
    
    def create(self, validated_data):
        return super().create(validated_data)


class StandardDetailSerializer(serializers.ModelSerializer):
    active_session_count = serializers.SerializerMethodField()
    teacher_name = serializers.ReadOnlyField(source='class_teacher.user.get_full_name')

    class Meta:
        model = Standard
        fields = ("id", "name", "description", "active_session_count","class_teacher","teacher_name")
        read_only_fields = fields

    def get_active_session_count(self, obj):
        # Accessing via related_name 'sessions' (as defined in your model)
        return obj.sessions.filter(status='ACTIVE').count()

# ────────────────────────────────────────────────
# 2. ClassroomSession Serializers
# ────────────────────────────────────────────────

class SessionCreateSerializer(serializers.ModelSerializer):
    # 'student_limit' ko API mein 'limit' dikhayenge
    limit = serializers.IntegerField(source='student_limit')
    
    # Organization ki UUID response mein laane ke liye
    organization_id = serializers.ReadOnlyField(source='organization.id')
    
    # Session code ko explicitly field mein daala taaki response mein aaye
    session_code = serializers.ReadOnlyField()

    class Meta:
        model = ClassroomSession
        # In fields ko response mein laane ke liye yahan add kiya
        fields = ("id", "session_code", "organization_id", "title", "purpose", 
                  "target_standard", "limit", "expires_at")

    def validate_expires_at(self, value):
        if value <= timezone.now():
            raise ValidationError("Expiry must be in the future.")
        return value

    # 2. Yahan smart validation lagayi
    def validate(self, attrs):
        user = self.context['request'].user
        purpose = attrs.get('purpose')
        target_standard = attrs.get('target_standard')

        # 🎯 SECURITY CHECK: Teacher sirf apni class ke liye session banaye
        if hasattr(user, 'teacher_profile'):
            teacher = user.teacher_profile
            
            # Agar session Students ke liye hai
            if purpose == 'STUDENT':
                if not target_standard:
                    raise ValidationError({"target_standard": "Bhai, class batana zaroori hai."})
                
                # Check: Kya ye wahi class hai jiska ye teacher 'class_teacher' hai?
                if target_standard.class_teacher != teacher:
                    raise PermissionDenied(
                        f"Bhai, aap sirf '{target_standard.name}' ke liye session nahi bana sakte "
                        "kyunki aap iske assigned class teacher nahi ho!"
                    )

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user
        
        if hasattr(user, "teacher_profile"):
            validated_data["teacher"] = user.teacher_profile
            validated_data["organization"] = user.teacher_profile.organization
        elif hasattr(user, "school_admin_profile"):
            validated_data["organization"] = user.school_admin_profile.organization
            validated_data["teacher"] = None 
        else:
            raise PermissionDenied("Only Teachers or Admins can create sessions.")
        
        return super().create(validated_data)

class SessionListSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.user.get_full_name", read_only=True)
    standard_name = serializers.CharField(source="target_standard.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    seats_remaining = serializers.SerializerMethodField()

    class Meta:
        model = ClassroomSession
        fields = (
            "id", "session_code", "teacher_name", "standard_name", 
            "student_limit", "current_student_count", "seats_remaining",
            "expires_at", "status", "status_display"
        )
        read_only_fields = fields

    def get_seats_remaining(self, obj):
        return obj.student_limit - obj.current_student_count

class SessionDetailSerializer(SessionListSerializer):
    # Re-using ListSerializer fields but adding more detail
    can_join = serializers.SerializerMethodField()

    class Meta(SessionListSerializer.Meta):
        fields = SessionListSerializer.Meta.fields + ("created_at", "can_join")

    def get_can_join(self, obj):
        return obj.status == 'ACTIVE' and obj.current_student_count < obj.student_limit

# ────────────────────────────────────────────────
# 3. Student & JoinRequest Serializers
# ────────────────────────────────────────────────

class JoinRequestCreateSerializer(serializers.ModelSerializer):
    session_code = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = JoinRequest
        fields = ("session_code",)

    def validate_session_code(self, value):
        try:
            # Session code check karna
            session = ClassroomSession.objects.get(session_code=value.upper(), status='ACTIVE')
            if session.current_student_count >= session.student_limit:
                raise ValidationError("Bhai, ye session full ho chuka hai.")
            self.context["session_obj"] = session
        except ClassroomSession.DoesNotExist:
            raise ValidationError("Invalid or inactive session code.")
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        
        # 🟢 NEW SECURITY CHECKS START HERE ──────────────────────────────
        
        # 🛑 1. Check: Kya ye Admin hai?
        if hasattr(user, 'school_admin_profile'):
            raise ValidationError("Bhai, aap Admin ho! Admin kabhi student nahi banta.")

        # 🛑 2. Check: Kya ye Teacher hai?
        if hasattr(user, 'teacher_profile'):
            raise ValidationError("Bhai, aap Teacher ho! Master hokar bench par mat baitho.")

        # 🛑 3. Check: Kya ye pehle se hi kisi class ka Student hai?
        if hasattr(user, 'student_profile'):
            student = user.student_profile
            # Agar student already kisi class ka member hai
            if student.current_standard:
                raise ValidationError(f"Aap pehle se hi {student.current_standard.name} ke student ho!")

        # 🟢 NEW SECURITY CHECKS END ────────────────────────────────────

        # Purana logic (Session object fetch karna)
        session = self.context.get("session_obj")

        # Duplicate Request Check
        if JoinRequest.objects.filter(session=session, user=user).exists():
            raise ValidationError("Aapne is session ke liye pehle hi request bhej di hai.")

        return attrs

    def create(self, validated_data):
        # Create method ab ekdum clean ho gaya
        return JoinRequest.objects.create(
            session=self.context["session_obj"], 
            user=self.context["request"].user
        )

class JoinRequestListSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source="user.get_full_name", read_only=True)
    session_info = serializers.CharField(source="session.session_code", read_only=True)

    class_teacher = serializers.CharField(source="session.teacher.user.get_full_name", read_only=True)
    
    class Meta:
        model = JoinRequest
        fields = ("id", "applicant_name", "session_info", "status", "created_at","class_teacher",)
        read_only_fields = fields


class AssignClassTeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Standard
        fields = ['class_teacher']

    def validate_class_teacher(self, value):
        user = self.context['request'].user
        # Check: Kya ye teacher usi school ka hai jiska admin request bhej raha hai?
        if value.organization != user.school_admin_profile.organization:
            raise serializers.ValidationError("Bhai, ye teacher aapke school ka nahi hai!")
        return value