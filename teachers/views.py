from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from .models import Teacher
from .serializers import TeacherPublicSerializer, TeacherProfileSerializer
from .permissions import IsTeacherOwnerOrSchoolAdmin

class TeacherViewSet(viewsets.ModelViewSet):
    """
    Objective #4, #5: Handle Independent & School Teachers
    """
    queryset = Teacher.objects.filter(is_active_teacher=True)
    permission_classes = [IsTeacherOwnerOrSchoolAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Marketplace Filtering
    filterset_fields = ['is_verified', 'preferred_mode', 'organization']
    search_fields = ['user__first_name', 'user__last_name', 'bio', 'subject_expertise']
    ordering_fields = ['hourly_rate', 'experience_years']

    def get_serializer_class(self):
        if self.action in ['list', 'marketplace']:
            return TeacherPublicSerializer
        return TeacherProfileSerializer

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        """Teacher apni profile /api/teachers/me/ par manage karega"""
        teacher = get_object_or_404(Teacher, user=request.user)
        if request.method == 'GET':
            serializer = TeacherProfileSerializer(teacher)
            return Response(serializer.data)
        
        serializer = TeacherProfileSerializer(teacher, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='join-school')
    def join_school_request(self, request):
        """
        Objective #3: Teacher join request logic using session_code.
        """
        # Circular import se bachne ke liye import yahan andar kiya hai
        from students_classroom.models import ClassroomSession, JoinRequest
        
        # 1. Frontend se Code uthao (e.g. "CLS-X7Y2Z")
        session_code = request.data.get('session_code') 
        
        if not session_code:
            return Response({"error": "Session code is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Database mein session check karo
        session = get_object_or_404(
            ClassroomSession.objects.active(), # Sirf wahi jo delete nahi hue
            session_code=session_code
        )

        # 3. Check karo session joinable hai (Time aur Capacity check)
        if not session.is_joinable:
            return Response(
                {"error": f"This session is currently {session.status}. It might be expired or full."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Join Request create karo (Ya existing wali uthao)
        join_request, created = JoinRequest.objects.get_or_create(
            session=session,
            user=request.user,
            defaults={'status': 'PENDING'}
        )

        if not created:
            return Response(
                {"message": f"You have already sent a request. Current status: {join_request.status}"}, 
                status=status.HTTP_200_OK
            )

        return Response(
            {"message": "Join request sent successfully! Wait for school admin to accept."}, 
            status=status.HTTP_201_CREATED
        )