from django.urls import path
from . import views

# app_name helps in URL reversing (industry best practice)
app_name = 'normaluser'

urlpatterns = [
    # --- AUTHENTICATION FLOW ---
    # 1. Account Discovery (First step of login - Mobile Based)
    path('auth/discover/', views.AccountDiscoveryView.as_view(), name='account-discovery'),
    
    # 2. Registration
    path('auth/signup/', views.SignupView.as_view(), name='signup'),
    
    # 3. Standard Login (Accepts username/email/mobile)
    path('auth/login/', views.LoginView.as_view(), name='login'),
    
    # 4. Logout
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),

    # --- USER PROFILE & SETTINGS ---
    # Soft delete (using 'me' indicates current authenticated user)
    path('me/delete/', views.UserSoftDeleteView.as_view(), name='user-soft-delete'),

    # Naya wala (Normal VijayLaxmi users ke liye)
    path('auth/signup/user/', views.NormalUserSignupView.as_view(), name='user-signup'),

    # --- DASHBOARD & INITIAL DATA ---
    path('me/dashboard-init/', views.DashboardDataView.as_view(), name='dashboard-init'),

    # shivam sir has made this url.
    path('me/', views.UserMeView.as_view(), name='user-me'),
]