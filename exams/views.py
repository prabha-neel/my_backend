from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Exam
from .serializers import ExamCreateSerializer, ExamDetailSerializer
from .permissions import IsAdminOrTeacher
from django.db import transaction  

class ExamViewSet(viewsets.ModelViewSet):
    """
    Industry Level ViewSet for Exam Timetables:
    - Admin/Teacher: Can create/edit/view all exams for their organization.
    - Student: Strictly restricted to their own class timetable.
    """
    permission_classes = [IsAdminOrTeacher]

    def get_serializer_class(self):
        # Create (POST) ke liye validation wala serializer, View (GET) ke liye detail wala
        if self.action == 'create':
            return ExamCreateSerializer
        return ExamDetailSerializer

    def get_queryset(self):
        user = self.request.user
        
        # 1. 🔍 Organization Fetching Logic
        # Chunki NormalUser mein direct field nahi hai, hum profile se nikalenge
        org = None
        
        if user.role == 'STUDENT':
            from students.models import StudentProfile
            try:
                profile = StudentProfile.objects.get(user=user)
                org = profile.organization # Student ki org uski profile se
                base_queryset = Exam.objects.filter(organization=org, target_standard=profile.current_standard)
            except StudentProfile.DoesNotExist:
                return Exam.objects.none()
        
        else:
            # School Admin ya Teacher ke liye Organization nikalna
            # school_admin_profile tune models.py mein related_name diya hai
            admin_profile = user.school_admin_profile.filter(is_active=True).first()
            if admin_profile:
                org = admin_profile.organization
                base_queryset = Exam.objects.filter(organization=org)
            else:
                return Exam.objects.none()

        # 2. 🛡️ Base Security & Optimization
        # Prefetch subjects taaki database queries kam ho (Performance)
        queryset = base_queryset.filter(is_active=True).prefetch_related('subjects').order_by('-start_date')

        # 3. ✅ Admin/Teacher Zone: Optional Filter by class name (?class_name=Class 10)
        if user.role != 'STUDENT':
            class_name = self.request.query_params.get('class_name')
            if class_name:
                queryset = queryset.filter(target_standard__name=class_name)

        return queryset

    def perform_create(self, serializer):
        # Serializer ke create method mein humne logic handle kiya hai
        serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        # 1. Validation check karo
        serializer.is_valid(raise_exception=True)
        
        # 2. Data save karo (Ye serializer ka create method call karega)
        self.perform_create(serializer)
        
        # 3. Headers taiyaar karo
        headers = self.get_success_headers(serializer.data)
        
        # 🔴 YE RETURN ZAROORI HAI (Iske bina NoneType error aati hai)
        return Response(
            {
                "status": "success",
                "message": "Exam Schedule created successfully for all sections!", 
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )
    
    def update(self, request, *args, **kwargs):
        """
        Industry Standard PUT/PATCH: 
        Ensures atomic updates so data doesn't get corrupted.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            self.perform_update(serializer)

        return Response({
            "status": "success",
            "message": "Exam schedule and subjects updated successfully!",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        Hard Delete Logic:
        Permanently removes the exam and its subjects from the database.
        Includes a safety check for ongoing/completed exams.
        """
        instance = self.get_object()
        exam_title = instance.exam_title # Logging ke liye naam rakh liya

        # 🛡️ Business Logic: Agar exam start ho gaya hai toh delete block kar do
        if hasattr(instance, 'status') and instance.status in ['ONGOING', 'COMPLETED']:
            return Response({
                "status": "error",
                "message": f"Cannot delete '{exam_title}' because it is already {instance.status}."
            }, status=status.HTTP_400_BAD_REQUEST)

        # 🟢 Permanent Hard Delete
        instance.delete() 

        return Response({
            "status": "success",
            "message": f"Exam '{exam_title}' and all related subjects have been permanently deleted."
        }, status=status.HTTP_200_OK)