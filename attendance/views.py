from attr import s
from django.db.models import Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from students_classroom.models import Standard
from .models import Attendance

class AttendanceSummaryView(APIView):
    """
    Returns nested JSON: Class -> Sections -> Counts
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. Date nikalna (Query param se ya Today)
        query_date = request.query_params.get('date', str(timezone.now().date()))
        
        # 2. Saare standards/classes ka data process karna
        standards = Standard.objects.all()
        summary_data = []

        # Unique class names (e.g., Class 1, Class 9)
        unique_class_names = standards.values_list('name', flat=True).distinct()

        for c_name in unique_class_names:
            class_sections = standards.filter(name=c_name)
            
            c_total, c_present, c_absent, c_leave = 0, 0, 0, 0
            sections_list = []

            for section in class_sections:
                # 🚩 DB Aggregation for each section
                stats = Attendance.objects.filter(
                    standard=section, 
                    date=query_date
                ).aggregate(
                    total=Count('id'),
                    present=Count('id', filter=Q(status='PRESENT')),
                    absent=Count('id', filter=Q(status='ABSENT')),
                    leave=Count('id', filter=Q(status='LEAVE'))
                )

                sec_json = {
                    "section_name": section.section,
                    "total_students": stats['total'] or 0,
                    "present_count": stats['present'] or 0,
                    "absent_count": stats['absent'] or 0,
                    "leave_count": stats['leave'] or 0,
                }
                
                sections_list.append(sec_json)
                
                # Class level calculation
                c_total += sec_json['total_students']
                c_present += sec_json['present_count']
                c_absent += sec_json['absent_count']
                c_leave += sec_json['leave_count']

            # Class ka pura data append karo
            summary_data.append({
                "class_name": c_name,
                "total_students": c_total,
                "present_count": c_present,
                "absent_count": c_absent,
                "leave_count": c_leave,
                "sections": sections_list
            })

        # 3. Final Output
        return Response({
            "success": True,
            "date": query_date,
            "data": summary_data
        })
    



class SectionAttendanceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        standard_id = request.query_params.get('standard_id')
        query_date = request.query_params.get('date', str(timezone.now().date()))

        if not standard_id:
            return Response({"error": "standard_id is required"}, status=400)

        # 1. Us section ke saare students uthao
        from students.models import StudentProfile
        students = StudentProfile.objects.filter(current_standard_id=standard_id, is_active=True)

        # 2. Check karo kiski attendance lag chuki hai
        attendance_records = Attendance.objects.filter(standard_id=standard_id, date=query_date)
        attendance_map = {a.student_id: a.status for a in attendance_records}

        # 3. List taiyar karo
        results = []
        for student in students:
            results.append({
                "student_id": student.id,
                "student_unique_id": student.student_unique_id,
                # "full_name": student.full_name,
                "full_name": f"{s.user.first_name} {s.user.last_name}",
                "status": attendance_map.get(student.id, "PENDING") # Agar record nahi hai toh PENDING dikhao
            })

        return Response({
            "success": True,
            "date": query_date,
            "data": results
        })