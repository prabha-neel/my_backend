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
from .serializers import SignupSerializer, LoginSerializer, AccountDeleteSerializer, NotificationSerializer
from .models import NormalUser, Notification
from .utils import create_notification

logger = logging.getLogger(__name__)


@extend_schema(
    description="Register a new user account",
    responses={
        201: OpenApiResponse(description="Account created successfully"),
        400: OpenApiResponse(description="Validation error"),
        409: OpenApiResponse(description="User already exists"),
    }
)
@method_decorator(ratelimit(key='ip', rate='2/m', method='POST', block=True), name='post')
class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "message": "Validation failed",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                user = serializer.save()
            create_notification(
                    user, 
                    "Welcome aboard! 🚀", 
                    f"Hi {user.first_name or user.username}, your account has been created successfully.", 
                    "success"
                )
        except IntegrityError:
            return Response({
                "success": False,
                "message": "A user with this username, email, or mobile number already exists."
            }, status=status.HTTP_409_CONFLICT)

        refresh = RefreshToken.for_user(user)

        return Response({
            "success": True,
            "message": "Account created successfully!",
            "data": {
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token)
                },
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "email": user.email,
                    "mobile": user.mobile
                }
            }
        }, status=status.HTTP_201_CREATED)


@extend_schema(
    description="User login via username, email, or mobile",
    responses={
        200: OpenApiResponse(description="Login successful"),
        400: OpenApiResponse(description="Invalid credentials"),
    }
)
@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='post')
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            login_attempt = request.data.get('user_name', 'unknown')
            ip = request.META.get('REMOTE_ADDR')
            logger.warning(f"Failed login attempt for '{login_attempt}' from IP: {ip}")
            return Response({
                "success": False,
                "message": "Invalid credentials. Please check your username/email/mobile or password.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        return Response({
            "success": True,
            "message": "Login successful!",
            "data": {
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token)
                },
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "email": user.email,
                    "mobile": user.mobile
                }
            }
        }, status=status.HTTP_200_OK)


@extend_schema(
    description="Logout user by blacklisting refresh token",
    responses={
        200: OpenApiResponse(description="Logout successful"),
        400: OpenApiResponse(description="Invalid or missing token"),
    }
)
@method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True), name='post')
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
        
# # views.py
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.permissions import AllowAny, IsAuthenticated
# from rest_framework_simplejwt.tokens import RefreshToken
# from rest_framework_simplejwt.exceptions import TokenError
# from rest_framework import status
# from django.db import transaction, IntegrityError
# from django.utils.decorators import method_decorator
# from django_ratelimit.decorators import ratelimit
# from drf_spectacular.utils import extend_schema
# import logging
# from rest_framework.throttling import UserRateThrottle
# from .serializers import SignupSerializer, LoginSerializer, AccountDeleteSerializer
# from .models import NormalUser

# logger = logging.getLogger(__name__)


# class SignupView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         serializer = SignupSerializer(data=request.data)
#         if not serializer.is_valid():
#             return Response({
#                 "success": False,
#                 "message": "Validation failed",
#                 "errors": serializer.errors
#             }, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             with transaction.atomic():
#                 user = serializer.save()
#         except IntegrityError:
#             return Response({
#                 "success": False,
#                 "message": "User with this username, email or mobile already exists."
#             }, status=status.HTTP_409_CONFLICT)

#         refresh = RefreshToken.for_user(user)
#         return Response({
#             "success": True,
#             "message": "Account created successfully!",
#             "tokens": {
#                 "refresh": str(refresh),
#                 "access": str(refresh.access_token)
#             },
#             "user": {
#                 "id": user.id,
#                 "username": user.username,
#                 "first_name": user.first_name,
#                 "email": user.email,
#                 "mobile": user.mobile
#             }
#         }, status=status.HTTP_201_CREATED)


# @method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='post')
# class LoginView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         serializer = LoginSerializer(data=request.data)
#         if not serializer.is_valid():
#             return Response({
#                 "success": False,
#                 "message": "Invalid credentials",
#                 "errors": serializer.errors
#             }, status=status.HTTP_400_BAD_REQUEST)

#         user = serializer.validated_data['user']
#         refresh = RefreshToken.for_user(user)

#         return Response({
#             "success": True,
#             "message": "Login successful!",
#             "tokens": {
#                 "refresh": str(refresh),
#                 "access": str(refresh.access_token)
#             },
#             "user": {
#                 "id": user.id,
#                 "username": user.username,
#                 "first_name": user.first_name,
#                 "email": user.email,
#                 "mobile": user.mobile
#             }
#         }, status=status.HTTP_200_OK)


# @method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True), name='post')
# class LogoutView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         refresh_token = request.data.get("refresh")
#         if not refresh_token:
#             return Response({"success": False, "detail": "Refresh token is required."}, status=400)
#         try:
#             token = RefreshToken(refresh_token)
#             token.blacklist()
#             return Response({"success": True, "detail": "Logout successful."}, status=200)
#         except TokenError:
#             return Response({"success": False, "detail": "Invalid or already blacklisted token."}, status=400)


# class AccountDeleteThrottle(UserRateThrottle):
#     rate = '3/day'


# class UserSoftDeleteView(APIView):
#     permission_classes = [IsAuthenticated]
#     throttle_classes = [AccountDeleteThrottle]

#     @transaction.atomic
#     def post(self, request):
#         user = request.user

#         if getattr(user, 'is_deleted', False):
#             return Response({"detail": "Account is already deleted."}, status=200)

#         serializer = AccountDeleteSerializer(data=request.data)
#         if not serializer.is_valid():
#             return Response(serializer.errors, status=400)

#         if not user.check_password(serializer.validated_data['password']):
#             return Response({"detail": "Incorrect password."}, status=403)

#         user.soft_delete(deleted_by=user)
#         logger.info(f"Account soft deleted | User ID: {user.id}")
#         return Response({"detail": "Account deleted successfully. We're sad to see you go!"}, status=200)
