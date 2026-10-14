from allauth.account.models import EmailAddress
from allauth.account.signals import email_confirmed
from django.conf import settings
from django.dispatch import receiver

from ai_risiko.airisiko.tasks import send_mail_task


@receiver(email_confirmed)
def email_confirmed(request, email_address, **kwargs):
    """
    Upon email confirmation, unset user.is_active pending Admin approval to
    manually set user.is_active to True.
    """
    new_email_address = EmailAddress.objects.get(email=email_address)
    user = new_email_address.user
    user.is_active = False
    user.save()
    email_recipients = []
    if settings.MANAGERS:
        email_recipients = [manager[1] for manager in settings.MANAGERS]
    email_recipients.append(new_email_address.email)
    send_mail_task.delay(
        f"[AI Risiko] E-mail address confirmed for {user.username}",
        "Thank you for confirming your e-mail address, your registration is pending for approval by the Administrator.",
        email_recipients,
    )
