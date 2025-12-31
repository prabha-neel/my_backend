from django.urls import path, include
from . import views

urlpatterns = [
    path('auth/signup/', views.SignupView.as_view(), name='signup'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/me/soft-delete/', views.UserSoftDeleteView.as_view(), name='user-soft-delete'),
]