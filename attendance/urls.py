from django.urls import path
from .views import AttendanceSummaryView, SaveAttendanceView, SectionAttendanceListView, MarkAttendanceView, StudentMonthlyAttendanceView, TeacherClassListView

urlpatterns = [
    # 1. Dashboard Summary (Class-wise counts)
    # URL: /api/v1/attendance/summary/
    path('summary/', AttendanceSummaryView.as_view(), name='attendance-summary'),

    # 2. Specific Class Student List (For marking)
    # URL: /api/v1/attendance/section-list/
    path('section-list/', SectionAttendanceListView.as_view(), name='section-attendance-list'),

    # 3. Bulk Mark/Save Attendance (POST)
    # URL: /api/v1/attendance/mark/
    path('mark/', MarkAttendanceView.as_view(), name='mark-attendance'),


    # ... purane paths ...
    path('student-report/', StudentMonthlyAttendanceView.as_view(), name='student-monthly-report'),


    path('teacher-register/', TeacherClassListView.as_view(), name='teacher-register'),
    path('save-register/', SaveAttendanceView.as_view(), name='save-register'),
]
