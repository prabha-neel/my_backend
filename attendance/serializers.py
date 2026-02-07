from rest_framework import serializers

class SectionSummarySerializer(serializers.Serializer):
    section_name = serializers.CharField()
    total_students = serializers.IntegerField()
    present_count = serializers.IntegerField()
    absent_count = serializers.IntegerField()
    leave_count = serializers.IntegerField()

class AttendanceSummarySerializer(serializers.Serializer):
    class_name = serializers.CharField()
    total_students = serializers.IntegerField()
    present_count = serializers.IntegerField()
    absent_count = serializers.IntegerField()
    leave_count = serializers.IntegerField()
    sections = SectionSummarySerializer(many=True)



class StudentAttendanceListSerializer(serializers.Serializer):
    student_id = serializers.IntegerField(source='id')
    student_unique_id = serializers.CharField()
    full_name = serializers.CharField()
    status = serializers.CharField() # PENDING, PRESENT, ABSENT, etc.