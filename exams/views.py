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
        school_id_from_header = self.request.headers.get('school-id') or self.request.headers.get('school_id')
        queryset = Exam.objects.none()

        # 1. STUDENT LOGIC (Same rahega)
        if user.role == 'STUDENT':
            from students.models import StudentProfile
            try:
                profile = StudentProfile.objects.get(user=user)
                # Student ko sirf uski class aur uske school ka data dikhega
                queryset = Exam.objects.filter(
                    organization=profile.organization, 
                    target_standard=profile.current_standard,
                    is_active=True
                )
            except StudentProfile.DoesNotExist:
                return Exam.objects.none()

        # 2. ADMIN/TEACHER LOGIC (Header Support ke saath)
        else:
            # Header se school_id uthao
            school_id_from_header = self.request.headers.get('school_id')
            
            # Check karo ki kya user is school se linked hai
            if school_id_from_header:
                admin_profile = user.school_admin_profile.filter(organization_id=school_id_from_header).first()
            else:
                # Agar header nahi hai, toh default active school uthao (purana logic)
                admin_profile = user.school_admin_profile.filter(is_active=True).first()

            if admin_profile:
                queryset = Exam.objects.filter(organization=admin_profile.organization, is_active=True)
            else:
                return Exam.objects.none()

        # 3. CLASS FILTER & PERFORMANCE (Same rahega)
        class_name = self.request.query_params.get('class_name')
        if class_name and user.role != 'STUDENT':
            queryset = queryset.filter(target_standard__name=class_name)

        return queryset.prefetch_related('subjects').order_by('-start_date')

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
    
    def get_serializer_context(self):
        """
        Ye method ensure karega ki 'school_id' hamesha serializer ke andar available rahe.
        """
        context = super().get_serializer_context()
        # Header se school_id uthao
        school_id = self.request.headers.get('school_id') or self.request.headers.get('school-id')
        
        # Context mein inject kar do
        context.update({"school_id_header": school_id})
        return context