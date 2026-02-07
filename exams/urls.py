from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExamViewSet

router = DefaultRouter()
router.register(r'schedule', ExamViewSet, basename='exam-schedule')

urlpatterns = [
    path('', include(router.urls)),
]