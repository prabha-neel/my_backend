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
    # 🎯 1. school_id ko input mein lenge (POST request ke liye)
    school_id = serializers.UUIDField(write_only=True, required=False)
    
    # 🎯 2. Organization field (Hidden) - backend handle karega
    organization = serializers.HiddenField(default=None)
    teacher_name = serializers.ReadOnlyField(source='class_teacher.user.get_full_name')

    class Meta:
        model = Standard
        fields = ("id", "school_id", "name", "description", "organization", "class_teacher", "teacher_name")
        read_only_fields = ("id", "teacher_name")

        # Validator waisa hi rahega
        validators = [
            UniqueTogetherValidator(
                queryset=Standard.objects.all(),
                fields=['organization', 'name'],
                message="Bhai, ye class is school mein pehle se bani hui hai!"
            )
        ]

    # 🎯 3. Yahan aati hai asli Surgery (validate method)
    def validate(self, attrs):
        user = self.context['request'].user
        # JSON body se school_id uthao
        school_id = attrs.get('school_id') or self.initial_data.get('school_id')

        # Admin Logic
        if hasattr(user, 'school_admin_profile') and user.school_admin_profile.exists():
            if not school_id:
                raise ValidationError({"school_id": "Admin bhai, school_id dena zaroori hai!"})
            
            # RelatedManager error se bachne ke liye filter use kiya
            admin_prof = user.school_admin_profile.filter(organization_id=school_id).first()
            if not admin_prof:
                raise ValidationError({"school_id": "Aap is school ke admin nahi ho!"})
            
            attrs['organization'] = admin_prof.organization
            
        # Teacher Logic (Safe fallback)
        elif hasattr(user, 'teacher_profile'):
            attrs['organization'] = user.teacher_profile.organization
        else:
            raise PermissionDenied("Sirf Admin ya Teacher hi class create kar sakte hain!")

        # school_id ko attrs se hata do taaki Model save karte waqt 'unexpected field' error na de
        attrs.pop('school_id', None)
        return attrs

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

# school_app/students_classroom/serializers.py

class SessionCreateSerializer(serializers.ModelSerializer):
    school_id = serializers.PrimaryKeyRelatedField(
        source='organization',
        queryset=Standard._meta.get_field('organization').remote_field.model.objects.all(),
        required=False, 
        allow_null=True
    )
    
    limit = serializers.IntegerField(source='student_limit')
    session_code = serializers.ReadOnlyField()

    class Meta:
        model = ClassroomSession
        fields = ("id", "session_code", "school_id", "title", "purpose", 
                  "target_standard", "limit", "expires_at")

    def validate(self, attrs):
        user = self.context['request'].user
        purpose = attrs.get('purpose', 'STUDENT')
        target_standard = attrs.get('target_standard')
        organization = attrs.get('organization')

        # -----------------------------------------------------------
        # 1. 🟢 CLASS TEACHER LOGIC
        # -----------------------------------------------------------
        if hasattr(user, 'teacher_profile'):
            teacher = user.teacher_profile
            attrs['purpose'] = 'STUDENT' # Teacher hiring nahi kar sakta
            attrs['organization'] = teacher.organization # Auto-set school
            
            if not target_standard:
                raise ValidationError({"target_standard": "Bhai, class select karna zaroori hai."})
            
            if target_standard.class_teacher != teacher:
                raise PermissionDenied(f"Aap sirf '{target_standard.name}' ke liye session bana sakte ho.")

        # -----------------------------------------------------------
        # 2. 🔵 ADMIN LOGIC
        # -----------------------------------------------------------
        elif hasattr(user, 'school_admin_profile'):
            if not organization:
                 raise ValidationError({"school_id": "Admin bhai, school_id dena zaroori hai."})
            
            # Check: Kya admin is school ka hai?
            if not user.school_admin_profile.filter(organization=organization).exists():
                raise PermissionDenied("Aap is school ke admin nahi ho!")

            # 🛡️ NEW ADDITION: Cross-School Safety Check
            # Pakka karo ki jo class (standard) select ki hai wo usi school ki hai
            if target_standard and target_standard.organization != organization:
                raise ValidationError({
                    "target_standard": f"Bhai, '{target_standard.name}' aapke select kiye huye school ki class nahi hai!"
                })

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        
        # Teacher ke liye auto-assign teacher profile
        if hasattr(user, 'teacher_profile'):
            validated_data['teacher'] = user.teacher_profile
            
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
        session = self.context.get("session_obj")

        if hasattr(user, 'school_admin_profile') and user.school_admin_profile is not None:
             # Ek aur extra safety: Agar OneToOne relationship hai toh aise check karo
             try:
                 if user.school_admin_profile:
                     raise ValidationError("Bhai, aap Admin ho! Aapko request bhejne ki zaroorat nahi.")
             except:
                 pass # Profile nahi hai toh aage badho

        # 🎯 Case A: TEACHER Recruitment Session
        if session.purpose == 'TEACHER':
            # ❌ NEW CHECK: Student teacher banne ke liye apply nahi kar sakta
            if hasattr(user, 'student_profile'):
                raise ValidationError("Bhai, aap abhi student ho! Pehle padhai poori karo phir teacher banna.")

            # Check: Kya ye user pehle se usi school mein teacher hai?
            if hasattr(user, 'teacher_profile'):
                if user.teacher_profile.organization == session.organization:
                    raise ValidationError("Bhai, aap pehle se is school mein Teacher ho!")

        # 🎯 Case B: STUDENT Admission Session (Tera Purana Logic)
        else:
            # Check: Teacher student banne ki koshish toh nahi kar raha?
            if hasattr(user, 'teacher_profile'):
                raise ValidationError("Bhai, aap Teacher ho! Master hokar bench par mat baitho.")

            # Check: Kya ye pehle se kisi class ka student hai?
            if hasattr(user, 'student_profile') and user.student_profile.current_standard:
                raise ValidationError(f"Aap pehle se hi {user.student_profile.current_standard.name} ke student ho!")

        # 🛑 2. Duplicate Request Check
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
        
        # 🎯 HEART & KIDNEY SAFE LOGIC:
        # Purani line (jo crash kar rahi thi): 
        # if value.organization != user.school_admin_profile.organization:
        
        # ✅ Nayi safe line (RelatedManager check):
        is_authorized = user.school_admin_profile.filter(organization=value.organization).exists()
        
        if not is_authorized:
            raise serializers.ValidationError("Bhai, ye teacher aapke managed school ka nahi hai!")
            
        return value
    


    # class SessionCreateSerializer(serializers.ModelSerializer):
    # # 🎯 FE 'school_id' (UUID) bhejega, backend use 'organization' model se map karega
    # school_id = serializers.PrimaryKeyRelatedField(
    #     source='organization',
    #     queryset=Standard._meta.get_field('organization').remote_field.model.objects.all(),
    #     required=True
    # )
    
    # # 'student_limit' ko API mein 'limit' dikhayenge
    # limit = serializers.IntegerField(source='student_limit')
    
    # # Response mein UUID dikhane ke liye
    # organization_id = serializers.ReadOnlyField(source='organization.id')
    
    # # Session code automatic banta hai, isliye ReadOnly
    # session_code = serializers.ReadOnlyField()

    # class Meta:
    #     model = ClassroomSession
    #     # 🎯 Fields mein 'school_id' add kar diya hai
    #     fields = ("id", "session_code", "school_id", "organization_id", "title", "purpose", 
    #               "target_standard", "limit", "expires_at")

    # def validate_expires_at(self, value):
    #     if value <= timezone.now():
    #         raise ValidationError("Expiry must be in the future.")
    #     return value

    # def validate(self, attrs):
    #     user = self.context['request'].user
    #     purpose = attrs.get('purpose')
    #     target_standard = attrs.get('target_standard')

    #     # 🎯 HEART (Old Logic): Teacher security check waisa hi hai
    #     if hasattr(user, 'teacher_profile'):
    #         teacher = user.teacher_profile
            
    #         if purpose == 'STUDENT':
    #             if not target_standard:
    #                 raise ValidationError({"target_standard": "Bhai, class batana zaroori hai."})
                
    #             # Check: Kya ye wahi class hai jiska ye teacher 'class_teacher' hai?
    #             if target_standard.class_teacher != teacher:
    #                 raise PermissionDenied(
    #                     f"Bhai, aap sirf '{target_standard.name}' ke liye session nahi bana sakte "
    #                     "kyunki aap iske assigned class teacher nahi ho!"
    #                 )
    #     return attrs

    # def create(self, validated_data):
    #     request = self.context.get("request")
    #     user = request.user
        
    #     # DRF 'source' ki wajah se 'school_id' ko 'organization' key mein convert kar deta hai
    #     selected_org = validated_data.get('organization')
        
    #     if hasattr(user, "teacher_profile"):
    #         # Teacher logic remains same
    #         validated_data["teacher"] = user.teacher_profile
    #         validated_data["organization"] = user.teacher_profile.organization
        
    #     elif hasattr(user, "school_admin_profile"):
    #         # 🎯 KIDNEY (New Logic): Multi-school admin check
    #         # Check karo: Kya ye admin sach mein is selected school ka admin hai?
    #         is_linked = user.school_admin_profile.filter(organization=selected_org).exists()
    #         if not is_linked:
    #             raise PermissionDenied("Bhai, aap is school ke admin nahi ho!")
            
    #         validated_data["organization"] = selected_org
    #         validated_data["teacher"] = None 
    #     else:
    #         raise PermissionDenied("Only Teachers or Admins can create sessions.")
        
    #     return super().create(validated_data)