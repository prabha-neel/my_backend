from django.utils.translation import gettext_lazy as _

class SessionStatus:
    ACTIVE = "ACTIVE"
    FULL = "FULL"
    EXPIRED = "EXPIRED"
    CLOSED = "CLOSED"

    CHOICES = (
        (ACTIVE, _("Active")),
        (FULL, _("Full")),
        (EXPIRED, _("Expired")),
        (CLOSED, _("Closed")),
    )

class JoinRequestStatus:
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

    CHOICES = (
        (PENDING, _("Pending")),
        (ACCEPTED, _("Accepted")),
        (REJECTED, _("Rejected")),
    )