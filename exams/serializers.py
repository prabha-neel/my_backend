from rest_framework import serializers
from .models import Exam, ExamSubject
from students_classroom.models import Standard
from django.db import transaction

# 1. Subject Serializer
class ExamSubjectSerializer(serializers.ModelSerializer):
    date = serializers.DateField(input_formats=['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%d'], format='%Y-%m-%d')
    start_time = serializers.TimeField(format='%I:%M %p', input_formats=['%I:%M %p', '%H:%M'])
    end_time = serializers.TimeField(format='%I:%M %p', input_formats=['%I:%M %p', '%H:%M'])

    class Meta:
        model = ExamSubject
        fields = ['id','subject_name', 'date', 'start_time', 'end_time', 'room_no', 'max_marks', 'passing_marks', 'instruction']

# 2. Detail Serializer (GET requests ke liye mast hai)
from rest_framework import serializers
from .models import Exam, ExamSubject
from students_classroom.models import Standard
from django.db import transaction

# 1. Subject Serializer (Same as before, keep it clean)
class ExamSubjectSerializer(serializers.ModelSerializer):
    date = serializers.DateField(input_formats=['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%d'], format='%Y-%m-%d')
    start_time = serializers.TimeField(format='%I:%M %p', input_formats=['%I:%M %p', '%H:%M'])
    end_time = serializers.TimeField(format='%I:%M %p', input_formats=['%I:%M %p', '%H:%M'])

    class Meta:
        model = ExamSubject
        fields = ['id', 'subject_name', 'date', 'start_time', 'end_time', 'room_no', 'max_marks', 'passing_marks', 'instruction']

# 2. Detail Serializer (For GET requests)
class ExamDetailSerializer(serializers.ModelSerializer):
    subjects = ExamSubjectSerializer(many=True, read_only=True)
    class_name = serializers.CharField(source='target_standard.name', read_only=True)
    start_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = ['id', 'external_id', 'exam_title', 'class_name', 'start_date', 'end_date', 'status', 'subjects']

    def get_start_date(self, obj):
        return f"{obj.start_date}T00:00:00.000" if obj.start_date else None

    def get_end_date(self, obj):
        return f"{obj.end_date}T00:00:00.000" if obj.end_date else None

# 3. Create/Update Serializer (The Fixed Version)
class ExamCreateSerializer(serializers.ModelSerializer):
    subjects = ExamSubjectSerializer(many=True)
    # SerializerMethodField taaki response mein "Class 40" wapas dikhe
    class_name = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = ['exam_title', 'class_name', 'start_date', 'end_date', 'academic_year', 'subjects']

    def get_class_name(self, obj):
        return obj.target_standard.name if obj.target_standard else None

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')
        school_id = request.data.get('school_id')

        if not school_id:
            raise serializers.ValidationError({"school_id": "Body mein 'school_id' bhejna zaroori hai!"})
            
        user = request.user
        admin_profile = user.school_admin_profile.filter(organization_id=school_id).first()

        if not admin_profile:
            raise serializers.ValidationError({"error": "Unauthorized: Aap is school ke admin nahi hain."})

        org = admin_profile.organization
        # Note: class_name logic handled via request.data since it's a MethodField
        class_name_input = request.data.get('class_name')
        
        std = Standard.objects.filter(name=class_name_input, organization=org).first()
        if not std:
            raise serializers.ValidationError({"class_name": f"Class '{class_name_input}' nahi mili."})

        subjects_data = validated_data.pop('subjects')
        
        exam = Exam.objects.create(
            organization=org,
            created_by=user,
            target_standard=std,
            **validated_data
        )
        
        exam_subjects = [
            ExamSubject(exam=exam, **item) for item in subjects_data
        ]
        ExamSubject.objects.bulk_create(exam_subjects)
        return exam

    @transaction.atomic
    def update(self, instance, validated_data):
        # 1. Subjects aur Request data nikaalo
        subjects_data = validated_data.pop('subjects', [])
        request_data = self.context.get('request').data
        class_name_input = request_data.get('class_name')

        # 2. Basic Fields Update (Title, Dates, etc.)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # 3. Class Update (Same logic)
        if class_name_input:
            std_match = Standard.objects.filter(
                name__iexact=str(class_name_input).strip(), 
                organization=instance.organization
            ).first()
            if std_match:
                instance.target_standard = std_match
            else:
                raise serializers.ValidationError({"class_name": "Class not found."})

        instance.save()

        # 4. 🔥 RESET SUBJECTS (Yahi hai magic!)
        # Purane saare subjects uda do
        instance.subjects.all().delete()

        # Naye subjects fresh create karo (bilkul create method ki tarah)
        new_subjects = [
            ExamSubject(exam=instance, **item) for item in subjects_data
        ]
        ExamSubject.objects.bulk_create(new_subjects)

        # 5. Final Refresh
        instance.refresh_from_db()
        return instance