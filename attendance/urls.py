from django.urls import path
from .views import AttendanceSummaryView, SectionAttendanceListView

app_name = 'attendance'

urlpatterns = [
    path('summary/', AttendanceSummaryView.as_view(), name='attendance-summary'),
    path('section-list/', SectionAttendanceListView.as_view(), name='section-attendance-list'),
]