from rest_framework import serializers
from .models import Attendance
from students.models import StudentProfile

# 1. Individual Student ki attendance dikhane ke liye (GET section-list)
class StudentAttendanceSerializer(serializers.ModelSerializer):
    student_id = serializers.IntegerField(source='student.id', read_only=True)
    student_unique_id = serializers.CharField(source='student.student_unique_id', read_only=True)
    full_name = serializers.CharField(source='student.full_name', read_only=True)

    class Meta:
        model = Attendance
        fields = ['student_id', 'student_unique_id', 'full_name', 'status', 'date']

# 2. Bulk Attendance Mark karne ke liye (POST request)
class MarkAttendanceSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=Attendance.STATUS_CHOICES)

class BulkAttendanceOpsSerializer(serializers.Serializer):
    standard_id = serializers.IntegerField()
    date = serializers.DateField()
    attendance_list = MarkAttendanceSerializer(many=True)

# 3. Dashboard Summary ke liye 
class SectionSummarySerializer(serializers.Serializer):
    section_id = serializers.IntegerField()
    section_name = serializers.CharField()
    total_students = serializers.IntegerField()
    present_count = serializers.IntegerField()
    absent_count = serializers.IntegerField()
    leave_count = serializers.IntegerField()

class AttendanceClassSummarySerializer(serializers.Serializer):
    class_name = serializers.CharField()
    total_students = serializers.IntegerField()
    present_count = serializers.IntegerField()
    absent_count = serializers.IntegerField()
    leave_count = serializers.IntegerField()
    sections = SectionSummarySerializer(many=True)