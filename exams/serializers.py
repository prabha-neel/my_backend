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
        fields = ['subject_name', 'date', 'start_time', 'end_time', 'room_no', 'max_marks', 'passing_marks', 'instruction']

# 2. Detail Serializer (GET requests ke liye mast hai)
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

# 3. Create/Update Serializer (PRO version with Header Support)
class ExamCreateSerializer(serializers.ModelSerializer):
    subjects = ExamSubjectSerializer(many=True)
    class_name = serializers.CharField(write_only=True)

    class Meta:
        model = Exam
        fields = ['exam_title', 'class_name', 'start_date', 'end_date', 'academic_year', 'subjects']

    @transaction.atomic
    def create(self, validated_data):
        # 1. 📥 Request Body se school_id nikalna
        # Note: Humne Serializer Fields mein iska naam nahi rakha, 
        # isliye validated_data ke bajaye direct request.data se uthayenge.
        request = self.context.get('request')
        school_id = request.data.get('school_id')

        if not school_id:
            raise serializers.ValidationError({
                "school_id": "Body mein 'school_id' (UUID) bhejna zaroori hai!"
            })
            
        user = request.user
        
        # 2. 🛡️ Verification: Kya Admin is school se juda hai?
        admin_profile = user.school_admin_profile.filter(organization_id=school_id).first()

        if not admin_profile:
            print(f"DEBUG: School ID {school_id} not linked to User {user}")
            raise serializers.ValidationError({
                "error": "Aapko is school ke liye schedule banane ki permission nahi hai!"
            })

        org = admin_profile.organization
        class_name = validated_data.pop('class_name')
        
        # 3. 🔍 Database mein Class (Standard) dhoondhna
        std = Standard.objects.filter(name=class_name, organization=org).first()
        
        if not std:
            raise serializers.ValidationError({
                "class_name": f"Is school (ID: {school_id}) mein '{class_name}' naam ki class nahi mili."
            })

        # 4. 📝 Main Exam Schedule Create karna
        subjects_data = validated_data.pop('subjects')
        
        exam = Exam.objects.create(
            organization=org,
            created_by=user,
            target_standard=std,
            **validated_data
        )
        
        # 5. 📚 Exam Subjects ko Bulk Create karna
        exam_subjects = [
            ExamSubject(
                exam=exam,
                subject_name=item['subject_name'],
                date=item['date'],
                start_time=item['start_time'],
                end_time=item['end_time'],
                room_no=item.get('room_no'),
                max_marks=item.get('max_marks', 100),
                passing_marks=item.get('passing_marks', 33),
                instruction=item.get('instruction')
            ) for item in subjects_data
        ]
        ExamSubject.objects.bulk_create(exam_subjects)
        
        return exam

    @transaction.atomic
    def update(self, instance, validated_data):
        # Update mein bhi hum ensure karte hain ki school change na ho jaye accidentally
        subjects_data = validated_data.pop('subjects', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if subjects_data is not None:
            instance.subjects.all().delete()
            exam_subjects = [ExamSubject(exam=instance, **item) for item in subjects_data]
            ExamSubject.objects.bulk_create(exam_subjects)

        return instance