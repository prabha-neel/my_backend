from .models import Notification

def create_notification(user, title, message, n_type='info'):
    Notification.objects.create(
        recipient=user,
        title=title,
        message=message,
        notification_type=n_type
    )