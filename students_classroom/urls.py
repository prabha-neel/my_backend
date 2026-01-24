from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StandardViewSet,
    ClassroomSessionViewSet,
    JoinRequestViewSet,
)

app_name = 'students_classroom'

# Router sabse efficient tarika hai
router = DefaultRouter(trailing_slash=True)
router.register(r'standards', StandardViewSet, basename='standard')
router.register(r'sessions', ClassroomSessionViewSet, basename='session')
router.register(r'join-requests', JoinRequestViewSet, basename='joinrequest') # 👈 Powerhouse line

urlpatterns = [
    # Router ke saare endpoints (/join/, /accept-request/, etc.) yahan se milenge
    path('', include(router.urls)),

    # Agar aapko purane manual paths 'my/' aur 'pending/' chahiye, toh unhe niche rakho
    path(
        'join-requests/my/', 
        JoinRequestViewSet.as_view({'get': 'list'}), 
        name='joinrequest-my-list'
    ),
]