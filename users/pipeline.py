from django.shortcuts import redirect
from django.urls import reverse
from .models import UserProfile

def create_user_profile(backend, user, response, *args, **kwargs):
    """
    Create user profile for social auth users if it doesn't exist
    """
    if not hasattr(user, 'profile'):
        profile = UserProfile.objects.create(
            user=user,
            role='APPLICANT'  # Default role for GitHub login
        )
        
        # If using GitHub, try to get additional information
        if backend.name == 'github':
            if response.get('name'):
                names = response['name'].split(' ', 1)
                user.first_name = names[0]
                if len(names) > 1:
                    user.last_name = names[1]
            
            if response.get('bio'):
                profile.bio = response['bio']
            
            if response.get('blog'):
                profile.website = response['blog']
            
            if response.get('location'):
                profile.location = response['location']
            
            # Save the profile and user
            profile.save()
            user.save()
    
    return {
        'user': user,
        'is_new': kwargs.get('is_new', False)
    }

def social_auth_role_handler(strategy, details, user=None, *args, **kwargs):
    if user:
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Set default role to APPLICANT if not set
        if not profile.role:
            profile.role = 'APPLICANT'
            profile.save()
        
        # Set redirect URL based on role
        if profile.role == 'APPLICANT':
            return {
                'redirect_url': reverse('users:applicant_dashboard')
            }
        elif profile.role == 'RECRUITER':
            return {
                'redirect_url': reverse('users:recruiter_dashboard')
            }
        else:
            return {
                'redirect_url': reverse('users:home')
            }
    return None 