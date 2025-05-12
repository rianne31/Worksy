from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Tests email configuration by sending a test email'

    def handle(self, *args, **kwargs):
        try:
            send_mail(
                'Test Email from Worksy',
                'This is a test email to verify email settings.',
                settings.DEFAULT_FROM_EMAIL,
                [settings.EMAIL_HOST_USER],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS('Test email sent successfully!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send email: {str(e)}')) 