from django.contrib.auth.backends import ModelBackend
from .models import NormalUser
from django.db.models import Q

class MultiUserMobileBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        # 1. EMAIL FAST PATH (Agar @ hai toh seedha email search karo)
        if "@" in username:
            # .filter().first() with exact match is way faster than __iexact in SQLite
            user = NormalUser.objects.filter(
                email=username.lower().strip(), # Exact match index use karega
                is_active=True, 
                is_deleted=False
            ).first()
            
            if user and user.check_password(password):
                return user
            return None

        # 2. USERNAME/MOBILE LOGIC
        if username.isdigit():
            # Mobile logic (Jo tune fast banayi thi)
            users = NormalUser.objects.filter(mobile=username, is_active=True, is_deleted=False)
            
            if not users.exists():
                return None

            if users.count() == 1:
                user = users.first()
                if user.check_password(password):
                    return user
            elif users.count() > 1 and request:
                # No hashing here = Super Fast response
                request.multiple_accounts = list(users)
                return None
        else:
            # Pure Username login (Non-digit)
            user = NormalUser.objects.filter(
                username=username, 
                is_active=True, 
                is_deleted=False
            ).first()
            if user and user.check_password(password):
                return user

        return None