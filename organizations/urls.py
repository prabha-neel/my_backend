from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrganizationViewSet, SchoolAdminViewSet

# Industry Standard: Namespace define karna zaroori hai
app_name = 'organizations'

# 1. Router setup: Ye automatically GET, POST, PUT, DELETE ke routes generate karega
router = DefaultRouter()

# URL: /api/v1/organizations/list/
router.register(r'', OrganizationViewSet, basename='organization-detail')

# URL: /api/v1/organizations/admins/
router.register(r'admins', SchoolAdminViewSet, basename='admin-profile')

# 2. URL Patterns
urlpatterns = [
    # Router dwara banaye gaye saare endpoints yahan include honge
    path('', include(router.urls)),
]

