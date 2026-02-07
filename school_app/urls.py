"""
URL configuration for school_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Existing apps
    path('normal_user/', include("normal_user.urls")),

    # Classroom module (industry standard versioned API)
    path('api/v1/classroom/', include('students_classroom.urls')),
    
    #Organiations module
    path('api/v1/organizations/', include('organizations.urls')),

    path('api/v1/students/', include('students.urls')),

    path('api/v1/parents/', include('parents.urls')),
    
    path('api/v1/teachers/', include('teachers.urls')),

    # Auth
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # API Schema & Docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/schema/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path('api/v1/exams/', include('exams.urls')),
]