# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status, generics
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.db import transaction, IntegrityError
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.throttling import UserRateThrottle
import logging
from .serializers import SignupSerializer, LoginSerializer, AccountDeleteSerializer, NotificationSerializer, NormalUserSignupSerializer
from .models import NormalUser, Notification
from .utils import create_notification
from organizations.serializers import OrganizationDetailSerializer, SchoolAdminUserSerializer
from organizations.models import Organization, SchoolAdmin
from .models import NormalUser, Notification, create_notification
from django.contrib.auth import authenticate 
from organizations.serializers import OrganizationLoginSerializer

logger = logging.getLogger(__name__)


@extend_schema(
    description="Register a new School Admin and Organization together",
    responses={201: OpenApiResponse(description="School and Admin created successfully")}
)
@method_decorator(ratelimit(key='ip', rate='2/m', method='POST', block=True), name='dispatch')
class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        org_name = data.get('name') 
        
        try:
            with transaction.atomic():
                # 1. User check (Multiple schools handling)
                user = NormalUser.objects.filter(mobile=data.get('admin_mobile')).first()
                
                if not user:
                    user_serializer = SignupSerializer(data={
                        "mobile": data.get('admin_mobile'),
                        "first_name": data.get('admin_name'), # <-- Ye zaroori hai prefix ke liye
                        "email": data.get('admin_email'),    # <-- Ye zaroori hai validation ke liye
                        "password": data.get('admin_password'),
                        "role": "SCHOOL_ADMIN",
                    })
                    if not user_serializer.is_valid():
                        return Response({"success": False, "errors": user_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                    user = user_serializer.save()
                else:
                    user.role = "SCHOOL_ADMIN"
                    user.save()

                # 2. Org creation
                if org_name:
                    new_org = Organization.objects.create(
                        name=org_name,
                        admin=user,
                        org_type=data.get('org_type', 'school'),
                        address=data.get('address', ''),
                        affiliation_board=data.get('affiliation_board', ''),
                        is_active=data.get('is_active', True),
                        is_verified=data.get('is_verified', True)
                    )
                    
                    SchoolAdmin.objects.create(
                        user=user,
                        organization=new_org,
                        designation="Owner/Founder"
                    )

                # 3. Notification (Bande ko welcome bolo)
                create_notification(
                    user, 
                    "Welcome Principal! 🏫", 
                    f"Organization {org_name} has been registered successfully.", 
                    "success"
                )

                refresh = RefreshToken.for_user(user)
                return Response({
                    "success": True,
                    "message": f"Organization '{org_name}' linked successfully!",
                    "data": {
                        "tokens": {"refresh": str(refresh), "access": str(refresh.access_token)},
                        "user": SchoolAdminUserSerializer(user).data
                    }
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Signup Error: {str(e)}")
            return Response({"success": False, "message": "Signup failed", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    description="User login via username, email, or mobile",
    responses={
        200: OpenApiResponse(description="Login successful"),
        400: OpenApiResponse(description="Invalid credentials"),
    }
)

@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        user_input = request.data.get('user_name')
        password = request.data.get('password')

        # 1. Multi-Account Check (Jaisa tumhara tha, waisa hi rakha hai)
        user = authenticate(request, username=user_input, password=password)

        if not user and hasattr(request, 'multiple_accounts'):
            accounts = [{
                "id": u.id, 
                "name": u.first_name, 
                "username": u.username,
                "role": u.role,
                "school_name": u.school_admin_profile.first().organization.name if u.school_admin_profile.exists() else "General"
            } for u in request.multiple_accounts]
            
            return Response({
                "success": True,
                "action": "SELECT_ACCOUNT",
                "message": "Multiple accounts found.",
                "data": { "accounts": accounts }
            }, status=status.HTTP_200_OK)

        # 2. Login Validation
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response({
                "success": False,
                "message": "Invalid credentials.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        # 3. User Data (Admin/Student logic)
        if user.role in ['SCHOOL_ADMIN', 'SUPER_ADMIN']:
            user_data = {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "email": user.email,
            "mobile": user.mobile,
            "role": user.role
        }
        else:
            user_data = SignupSerializer(user).data

        # 4. 🔥 SCHOOLS LIST FIX (No more null/empty)
        schools_list = []
        org_data = None

        # RelatedManager (.all()) se list nikalna
        profiles = user.school_admin_profile.all() 
        
        # for p in profiles:
        #     schools_list.append({
        #         "school_id": p.organization.id,
        #         "school_name": p.organization.name,
        #         "org_id": p.organization.org_id,
        #         "designation": p.designation,
        #         "is_active": p.is_active
        #     })

        # 5. Default Organization Detail (Pehle school ki full details)
        if profiles.exists():
            try:
                # Sirf tabhi details fetch karo jab schools hon
                from organizations.serializers import OrganizationLoginSerializer
                first_org = profiles.first().organization
                org_data = OrganizationLoginSerializer(first_org).data
            except Exception as e:
                logger.error(f"Organization Detail Fetch Error: {str(e)}")
                org_data = None

        # 6. Final Response (Same structure as before)
        return Response({
            "success": True,
            "message": "Login successful!",
            "data": {
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token)
                },
                "user": user_data,
                "organization": org_data,
                # "schools": schools_list
            }
        }, status=status.HTTP_200_OK)


@extend_schema(
    description="Discover accounts linked to a mobile number",
    responses={200: OpenApiResponse(description="List of accounts found")}
)
class AccountDiscoveryView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        mobile = request.data.get('mobile')
        if not mobile:
            return Response({
                "success": False, 
                "message": "Mobile number is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Hamare SoftDeleteManager (.active_objects) ka use karke bache dhoondo
        users = NormalUser.active_objects.filter(mobile=mobile)

        if not users.exists():
            return Response({
                "success": False, 
                "message": "No account found with this mobile number"
            }, status=status.HTTP_404_NOT_FOUND)

        # Frontend ke liye data taiyar karo
        user_list = [{
            "username": user.username, # Ye frontend piche chupa lega
            "display_name": f"{user.first_name} {user.last_name}".strip() or user.username,
            "role": user.role,
            "email": user.email
        } for user in users]

        return Response({
            "success": True,
            "data": user_list
        }, status=status.HTTP_200_OK)
    
@extend_schema(
    description="Logout user by blacklisting refresh token",
    responses={
        200: OpenApiResponse(description="Logout successful"),
        400: OpenApiResponse(description="Invalid or missing token"),
    }
)
@method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True), name='dispatch')
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({
                "success": False,
                "message": "Refresh token is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({
                "success": True,
                "message": "Logout successful."
            }, status=status.HTTP_200_OK)
        except TokenError as e:
            return Response({
                "success": False,
                "message": "Invalid or already blacklisted token."
            }, status=status.HTTP_400_BAD_REQUEST)


class AccountDeleteThrottle(UserRateThrottle):
    rate = '3/day'  # 3 attempts per day per user


@extend_schema(
    description="Soft delete authenticated user's account after password verification",
    responses={
        200: OpenApiResponse(description="Account deleted or already deleted"),
        400: OpenApiResponse(description="Invalid request"),
        403: OpenApiResponse(description="Incorrect password"),
    }
)
class UserSoftDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AccountDeleteThrottle]

    @transaction.atomic
    def post(self, request):
        user = request.user

        if getattr(user, 'is_deleted', False):
            return Response({
                "success": False,
                "message": "Your account is already deleted."
            }, status=status.HTTP_200_OK)

        serializer = AccountDeleteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "message": "Validation failed",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(serializer.validated_data['password']):
            logger.warning(f"Failed account deletion attempt by user ID: {user.id} (wrong password)")
            return Response({
                "success": False,
                "message": "Incorrect password."
            }, status=status.HTTP_403_FORBIDDEN)

        user.soft_delete(deleted_by=user)
        logger.info(f"Account successfully soft-deleted | User ID: {user.id} | IP: {request.META.get('REMOTE_ADDR')}")

        return Response({
            "success": True,
            "message": "Account deleted successfully. We're sad to see you go!"
        }, status=status.HTTP_200_OK)


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Sirf wahi notifications dikhao jo logged-in user ke hain
        return Notification.objects.filter(recipient=self.request.user)

class MarkNotificationReadView(generics.UpdateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, recipient=request.user)
            notification.is_read = True
            notification.save()
            return Response({"success": True, "message": "Marked as read"})
        except Notification.DoesNotExist:
            return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)
    

@extend_schema(
    description="Register a new independent user (GUEST)",
    request=NormalUserSignupSerializer,
    responses={
        201: OpenApiResponse(description="User created successfully"),
        400: OpenApiResponse(description="Validation error"),
        429: OpenApiResponse(description="Too many requests"),
    }
)
# IP-based Rate Limiting: Ek minute mein sirf 2 signup attempts allowed hain ek IP se
@method_decorator(ratelimit(key='ip', rate='2/m', method='POST', block=True), name='dispatch')
class NormalUserSignupView(APIView):
    permission_classes = [AllowAny]
    # DRF ki apni throttling bhi backup ke liye
    throttle_classes = [UserRateThrottle] 

    @transaction.atomic
    def post(self, request):
        ip = request.META.get('REMOTE_ADDR')
        logger.info(f"Signup attempt started from IP: {ip}")

        serializer = NormalUserSignupSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                user = serializer.save()
                
                # 1. Welcome Notification
                try:
                    create_notification(
                        user, 
                        "Welcome! 🎉", 
                        f"Hello {user.first_name}, your account is ready.", 
                        "success"
                    )
                except Exception as e:
                    logger.error(f"Notification failed for {user.email}: {str(e)}")

                # 2. JWT Generation
                refresh = RefreshToken.for_user(user)
                
                logger.info(f"User created successfully: {user.email} from IP: {ip}")

                return Response({
                    "success": True,
                    "message": "Signup successful!",
                    "data": {
                        "tokens": {
                            "refresh": str(refresh),
                            "access": str(refresh.access_token),
                        },
                        "user": {
                            "id": user.id,
                            "name": user.first_name,
                            "email": user.email,
                            "role": user.role
                        }
                    }
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                logger.critical(f"System error during signup for IP {ip}: {str(e)}")
                return Response({
                    "success": False,
                    "message": "Internal server error. Please try later.",
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3. Security Logging for Validation Failures
        logger.warning(f"Validation failed for signup attempt from IP {ip}: {serializer.errors}")
        
        return Response({
            "success": False,
            "message": "Invalid data provided.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    

@method_decorator(ratelimit(key='user', rate='20/m', method='GET', block=True), name='dispatch')
class DashboardDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Performance: select_related database load kam karta hai
        profiles = user.school_admin_profile.select_related('organization').all()
        
        schools_list = []
        for p in profiles:
            # Check if organization exists to avoid errors
            if p.organization:
                schools_list.append({
                    "id": p.organization.id,
                    "org_id": p.organization.org_id,
                    "name": p.organization.name,
                    "role": p.designation or user.role, # Role profile se lena zyada sahi hai
                    "location": f"{p.organization.address or ''}"
                })

        first_profile = profiles.first()
        first_org = first_profile.organization if first_profile else None
        
        return Response({
            "success": True,
            "message": "Dashboard data fetched successfully",
            "unread_count": 12,
            "active_sessions": 5,
            "admin_name": f"{user.first_name} {user.last_name}".strip(),
            "admin_email": user.email,
            "school_id": first_org.id if first_org else None,
            "org_id": first_org.org_id if first_org else None,
            "organization_name": first_org.name if first_org else None,
            # Logo URL fix: media handling safe rahegi
            "organization_logo": request.build_absolute_uri(first_org.logo.url) if first_org and first_org.logo else None,
            "schoolsList": schools_list
        })
    

# This view has made by shivam sir. i wrote this line to remind me. 

@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='dispatch')
class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Base user data
        serializer = UserIdentitySerializer(user)
        user_data = serializer.data
        
        # Extra: Agar SCHOOL_ADMIN hai toh organizations bhi bhej do
        schools = []
        if user.role == 'SCHOOL_ADMIN':
            profiles = user.school_admin_profile.all()
            schools = [{
                "id": p.organization.id,
                "name": p.organization.name,
                "org_id": p.organization.org_id,
                "designation": p.designation
            } for p in profiles]

        return Response({
            "success": True,
            "data": {
                "user": user_data,
                "schools": schools # Dashboard pe redirect karne ke liye kaam aayega
            }
        }, status=status.HTTP_200_OK)