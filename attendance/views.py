from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Count, Q
from django.utils import timezone
from django.db import transaction
from students.models import StudentProfile

# Model imports
from students_classroom.models import Standard
from .models import Attendance

class StudentMonthlyAttendanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student_id = request.query_params.get('student_id')
        month = request.query_params.get('month') # Format: 02
        year = request.query_params.get('year')   # Format: 2026

        if not all([student_id, month, year]):
            return Response({"error": "student_id, month, and year are required"}, status=400)

        # 1. Student ki info uthao
        from students.models import StudentProfile
        try:
            student = StudentProfile.objects.get(id=student_id)
        except StudentProfile.DoesNotExist:
            return Response({"error": "Student not found"}, status=404)

        # 2. Monthly attendance records fetch karo
        attendance_records = Attendance.objects.filter(
            student_id=student_id,
            date__year=year,
            date__month=month
        ).order_by('date')

        # 3. Monthly log dictionary taiyaar karo (P/A/L mapping)
        # Status code mapping: PRESENT -> P, ABSENT -> A, LEAVE -> L
        status_map = {'PRESENT': 'P', 'ABSENT': 'A', 'LEAVE': 'L'}
        monthly_log = {}
        
        for record in attendance_records:
            date_str = record.date.strftime('%Y-%m-%d')
            monthly_log[date_str] = status_map.get(record.status, 'P')

        # 4. Final Data taiyaar karo
        # Note: 'status' field hum aaj ki attendance dikhane ke liye use kar sakte hain
        today = timezone.now().date()
        today_record = attendance_records.filter(date=today).first()
        today_status = today_record.status.capitalize() if today_record else "Pending"

        response_data = {
            "data": {
                "student_id": student.id,
                "name": f"{student.user.first_name} {student.user.last_name}",
                "roll_no": getattr(student, 'roll_no', 'N/A'), # Agar roll_no field hai toh
                "status": today_status,
                "monthly_log": monthly_log
            }
        }

        return Response(response_data)

class AttendanceSummaryView(APIView):
    """Dashboard Counts: Class -> Section -> P/A/L"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query_date = request.query_params.get('date', str(timezone.now().date()))
        standards = Standard.objects.all()
        summary_data = []
        unique_class_names = standards.values_list('name', flat=True).distinct()

        for c_name in unique_class_names:
            class_sections = standards.filter(name=c_name)
            sections_list = []
            for section in class_sections:
                stats = Attendance.objects.filter(standard=section, date=query_date).aggregate(
                    total=Count('id'),
                    present=Count('id', filter=Q(status='PRESENT')),
                    absent=Count('id', filter=Q(status='ABSENT')),
                    leave=Count('id', filter=Q(status='LEAVE'))
                )
                sections_list.append({
                    "section_id": section.id,
                    "section_name": section.section,
                    "total_students": stats['total'] or 0,
                    "present_count": stats['present'] or 0,
                    "absent_count": stats['absent'] or 0,
                    "leave_count": stats['leave'] or 0,
                })
            summary_data.append({"class_name": c_name, "sections": sections_list})

        return Response({"success": True, "date": query_date, "data": summary_data})

class SectionAttendanceListView(APIView):
    """Individual Student Status for a specific Class"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        standard_id = request.query_params.get('standard_id')
        query_date = request.query_params.get('date', str(timezone.now().date()))

        if not standard_id:
            return Response({"error": "standard_id is required"}, status=400)

        from students.models import StudentProfile
        students = StudentProfile.objects.filter(current_standard_id=standard_id, is_active=True)
        attendance_map = {a.student_id: a.status for a in Attendance.objects.filter(standard_id=standard_id, date=query_date)}

        results = []
        for s in students:
            results.append({
                "student_id": s.id,
                "student_unique_id": s.student_unique_id,
                "full_name":f"{s.user.first_name} {s.user.last_name}",
                "status": attendance_map.get(s.id, "PENDING")
            })
        return Response({"success": True, "date": query_date, "data": results})

class MarkAttendanceView(APIView):
    """POST to save/update daily attendance"""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        standard_id = request.data.get('standard_id')
        date = request.data.get('date', str(timezone.now().date()))
        attendance_list = request.data.get('attendance_list', [])

        if not standard_id:
            return Response({"error": "standard_id is required"}, status=400)

        Attendance.objects.filter(standard_id=standard_id, date=date).delete()
        entries = [Attendance(student_id=item['student_id'], standard_id=standard_id, 
                              date=date, status=item['status'], marked_by=request.user) 
                   for item in attendance_list]
        Attendance.objects.bulk_create(entries)
        return Response({"success": True, "message": "Attendance Saved!"})
    

# ===========================================================================================
# %%%%%%%%%%%%%%%%%%%%%%%%%%%% class teacher's class studnet list %%%%%%%%%%%%%%%%%%%%%%%%%%%
# ===========================================================================================

class TeacherClassListView(APIView):
    """
    Teacher jis class ka class-teacher hai, uske baccho ki list laane ke liye
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Maan lete hain teacher ke profile mein 'assigned_standard' linked hai
        # Agar nahi hai, toh hum 'standard_id' query param se le sakte hain
        standard_id = request.query_params.get('standard_id')

        if not standard_id:
            return Response({"error": "Standard ID is required"}, status=400)

        # Us specific class ke saare bacche uthao
        students = StudentProfile.objects.filter( # pyright: ignore[reportUndefinedVariable]
            current_standard_id=standard_id, 
            is_active=True
        ).select_related('user')

        # Aaj ki attendance status check karo (agar pehle se mark ho gayi ho)
        today = timezone.now().date()
        attendance_map = {
            a.student_id: a.status for a in Attendance.objects.filter(
                standard_id=standard_id, 
                date=today
            )
        }

        results = []
        for s in students:
            results.append({
                "student_id": s.id,
                "student_unique_id": s.student_unique_id,
                "full_name":f"{s.user.first_name} {s.user.last_name}",# Teri banayi hui property use ho rahi hai
                "status": attendance_map.get(s.id, "PENDING") # Default Pending
            })

        return Response({
            "success": True,
            "standard_id": standard_id,
            "date": str(today),
            "data": results
        })

class SaveAttendanceView(APIView):
    """
    Teacher jab 'Submit' dabayega tab saara data yahan aayega
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        standard_id = request.data.get('standard_id')
        attendance_date = request.data.get('date', str(timezone.now().date()))
        attendance_list = request.data.get('attendance_list', []) # List of {student_id, status}

        if not standard_id or not attendance_list:
            return Response({"error": "Invalid data provided"}, status=400)

        # Purani attendance delete karo (Update logic)
        Attendance.objects.filter(standard_id=standard_id, date=attendance_date).delete()

        # Nayi entries taiyaar karo
        new_records = []
        for item in attendance_list:
            new_records.append(
                Attendance(
                    student_id=item['student_id'],
                    standard_id=standard_id,
                    date=attendance_date,
                    status=item['status'],
                    marked_by=request.user # Teacher ki ID save ho rahi hai
                )
            )

        # Bulk save
        Attendance.objects.bulk_create(new_records)

        return Response({
            "success": True,
            "message": f"Attendance for {len(new_records)} students marked successfully!"
        }, status=status.HTTP_201_CREATED)