from rest_framework import serializers
from .models import Exam, ExamSubject
from students_classroom.models import Standard
from django.db import transaction

# 1. Subject Serializer (Reusable for both Create and Detail)
class ExamSubjectSerializer(serializers.ModelSerializer):
    date = serializers.DateField(input_formats=['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%d'], format='%Y-%m-%d')
    start_time = serializers.TimeField(format='%I:%M %p', input_formats=['%I:%M %p', '%H:%M'])
    end_time = serializers.TimeField(format='%I:%M %p', input_formats=['%I:%M %p', '%H:%M'])

    class Meta:
        model = ExamSubject
        fields = ['subject_name', 'date', 'start_time', 'end_time', 'room_no', 'max_marks', 'passing_marks', 'instruction']

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

# 3. Create Serializer (For POST/PUT requests) - Iska naam missing tha!
class ExamCreateSerializer(serializers.ModelSerializer):
    subjects = ExamSubjectSerializer(many=True)
    class_name = serializers.CharField(write_only=True)

    class Meta:
        model = Exam
        fields = ['exam_title', 'class_name', 'start_date', 'end_date', 'academic_year', 'subjects']

    @transaction.atomic
    def create(self, validated_data):
        subjects_data = validated_data.pop('subjects')
        class_name = validated_data.pop('class_name') # "Class 5"
        
        request = self.context.get('request')
        user = request.user
        admin_profile = user.school_admin_profile.filter(is_active=True).first()
        org = admin_profile.organization

        # 🔍 Hum abhi bhi check karenge ki ye class exist karti hai ya nahi
        # Lekin hum kisi bhi ek section (A ya B) ko target_standard bana denge
        # Taaki database integrity bani rahe, par logic common chale.
        std = Standard.objects.filter(name=class_name, organization=org).first()

        if not std:
            raise serializers.ValidationError({"class_name": f"'{class_name}' naam ki koi class nahi mili."})

        # 🟢 Sirf EK Exam record create hoga pure class ke liye
        exam = Exam.objects.create(
            organization=org,
            created_by=user,
            target_standard=std, 
            **validated_data
        )
        
        # Subjects create karo
        exam_subjects = [ExamSubject(exam=exam, **item) for item in subjects_data]
        ExamSubject.objects.bulk_create(exam_subjects)
        
        return exam

    @transaction.atomic
    def update(self, instance, validated_data):
        subjects_data = validated_data.pop('subjects', None)
        
        # Base fields update
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Subjects update (Hard refresh)
        if subjects_data is not None:
            instance.subjects.all().delete()
            exam_subjects = [ExamSubject(exam=instance, **item) for item in subjects_data]
            ExamSubject.objects.bulk_create(exam_subjects)

        return instance