"""
Django settings for school_app project.
"""

from pathlib import Path
from datetime import timedelta
import os  # <-- ADD: Environment variables ke liye

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY: Secret Key environment se load kar (best practice)
SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY',
    'django-insecure-2b)14@&)v#m%sxf6kf9*2y**g52)e%-(f5m7$d$%#d^mj7b3&)'  # fallback local ke liye
)

# DEBUG: Production mein False
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

# ALLOWED_HOSTS: Development mein local, production mein domain
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']
# Production mein add karna: 'api.yourschoolapp.com'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_filters',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',                     # <-- ADD: JWT ke liye zaruri
    'rest_framework_simplejwt.token_blacklist',     # <-- blacklist support
    'phonenumber_field',
    'corsheaders',                                  # Browser-based frontend (React/Angular) ke liye
    'drf_spectacular',   #<--- This line is for Schema documentation, Hit this URL :-> http://127.0.0.1:8000/api/schema/docs/

    # Local apps
    'normal_user',
    'organizations',
    'teachers',
    'students',
    'parents',
    'students_classroom', 
]

# MIDDLEWARE - CORS sabse upar hona chahiye
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # <-- ADD: Top pe
    'normal_user.middleware.RatelimitJSONMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'school_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'school_app.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'  # <-- CHANGE: India ke liye better
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # <-- ADD: deploy ke liye collectstatic

# Media files (future mein profile pic etc.)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Custom User Model - Already sahi
AUTH_USER_MODEL = 'normal_user.NormalUser'

# Custom Authentication Backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # Default login (Username/Email)
    'normal_user.backends.MultiUserMobileBackend',  # Tera naya logic (Mobile/Multiple Accounts)
]

# DRF Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.ScopedRateThrottle',
        'rest_framework.throttling.UserRateThrottle',  # <-- Ye added hai
        'rest_framework.throttling.AnonRateThrottle',  # <-- Ye added hai
    ],
    'DEFAULT_THROTTLE_RATES': {
        'organization_api': '100/day',
        'user': '1000/day',   # <-- Ye line zaroori hai (Fixes the KeyError: 'user')
        'anon': '100/day',    # <-- Safety ke liye
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# JWT Settings - Tera improved version (perfect!)
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# CORS Settings - Mobile App ke liye MOST IMPORTANT
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8000",
    # Production mein app ka actual origin daalna
]

# Development mein sab allow kar (temporary)
CORS_ALLOW_ALL_ORIGINS = True if DEBUG else False

# Rate Limiting Settings (optional but recommended)
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'