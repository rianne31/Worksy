from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.urls import reverse
from django.http import HttpResponseRedirect
from allauth.account.models import EmailAddress
from django.core.mail import send_mail
from django.conf import settings

class CustomAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        # Check user role and redirect accordingly
        if request.user.profile.role == 'APPLICANT':
            return reverse('users:applicant_dashboard')
        elif request.user.profile.role == 'RECRUITER':
            return reverse('users:recruiter_dashboard')
        else:
            # If no role, redirect to home
            return reverse('users:home')
    
    def send_confirmation_mail(self, request, emailconfirmation, signup):
        """
        Sends the confirmation email to both primary and secondary email addresses
        """
        current_site = request.site
        activate_url = self.get_email_confirmation_url(request, emailconfirmation)
        ctx = {
            "user": emailconfirmation.email_address.user,
            "activate_url": activate_url,
            "current_site": current_site,
            "key": emailconfirmation.key,
        }
        
        subject = f"{settings.ACCOUNT_EMAIL_SUBJECT_PREFIX}Please Confirm Your Email Address"
        message = f"""
        Hello from {current_site.name}!

        You're receiving this email because you or someone else has requested email verification for your user account.
        
        To confirm this is correct, go to {activate_url}
        
        If you did not request this, you can safely ignore this email.
        """
        
        # Send email using Django's send_mail
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[emailconfirmation.email_address.email],
            fail_silently=False,
        )
    
    def add_message(self, request, level, message_template, message_context=None, extra_tags=''):
        """
        Wrapper for `django.contrib.messages.add_message`, that reads the message text from a template.
        """
        if 'email confirmation' in message_template.lower():
            message_template = "Verification email sent. Please check your email to verify your account."
        super().add_message(request, level, message_template, message_context, extra_tags)

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_connect_redirect_url(self, request, socialaccount):
        return reverse('home')
    
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        # Social login users will need to sign up through regular forms
        # to get assigned a specific role
        return user

