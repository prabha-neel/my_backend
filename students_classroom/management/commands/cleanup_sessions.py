from django.core.management.base import BaseCommand
from django.utils import timezone
from students_classroom.models import ClassroomSession

class Command(BaseCommand):
    help = 'Expires ho chuke sessions ko database se permanently delete karta hai'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Wo saare sessions dhoondo jinka time khatam ho chuka hai
        expired_sessions = ClassroomSession.objects.filter(expires_at__lt=now)
        count = expired_sessions.count()
        
        if count > 0:
            expired_sessions.delete()
            self.stdout.write(self.style.SUCCESS(f'Safai Done! {count} expired sessions uda diye gaye.'))
        else:
            self.stdout.write(self.style.SUCCESS('Koi expired session nahi mila. Sab saaf hai!'))