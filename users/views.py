from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.backends import ModelBackend
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect, csrf_exempt
from django.middleware.csrf import get_token
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage, send_mail
from django.contrib.sites.shortcuts import get_current_site
from .tokens import account_activation_token
from .models import UserProfile, Conversation, Message, ChatbotConversation, ChatbotMessage, Company
from notifications.models import Notification
from .forms import UserProfileForm, MessageForm, ChatbotMessageForm, RecruiterSignupForm, ApplicantSignupForm
from jobs.models import JobApplication, Job, Company, Interview
from ai_matching.models import JobRecommendation
from django.utils import timezone
import json
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from datetime import timedelta
from django.conf import settings
import os

def home(request):
    # If user is logged in, redirect to appropriate dashboard based on role
    if request.user.is_authenticated:
        if request.user.profile.role == 'APPLICANT':
            return redirect('users:applicant_dashboard')
        elif request.user.profile.role == 'RECRUITER':
            return redirect('users:recruiter_dashboard')
    
    # Otherwise show the home page
    from jobs.views import home as jobs_home
    return jobs_home(request)

def applicant_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                # Get or create profile if it doesn't exist
                profile, created = UserProfile.objects.get_or_create(user=user)
                
                # Check if user is active
                if not user.is_active:
                    messages.error(request, "Your account is not activated. Please check your email for the activation link.")
                    return redirect('users:applicant_login')
                
                # Check if user is an applicant or if role is not set
                if profile.role == 'APPLICANT' or not profile.role:
                    # Set role to APPLICANT if not set
                    if not profile.role:
                        profile.role = 'APPLICANT'
                        profile.save()
                    
                    login(request, user)
                    messages.success(request, f"Welcome back, {username}!")
                    return redirect('users:applicant_dashboard')
                else:
                    messages.error(request, "This account is not registered as a job seeker.")
                    return redirect('users:applicant_login')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
        # Add Bootstrap classes to form fields
        form.fields['username'].widget.attrs.update({'class': 'form-control'})
        form.fields['password'].widget.attrs.update({'class': 'form-control'})
    
    return render(request, 'users/applicant_login.html', {'form': form})

@ensure_csrf_cookie
@csrf_protect
def recruiter_login(request):
    """
    Handle recruiter login with proper CSRF protection
    """
    # Set CSRF cookie
    get_token(request)
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                # Check if user is a recruiter
                profile, created = UserProfile.objects.get_or_create(user=user)
                
                # Check if user is active
                if not user.is_active:
                    messages.error(request, "Your account is not activated. Please check your email for the activation link.")
                    return redirect('users:recruiter_login')
                
                if profile.role != 'RECRUITER':
                    messages.error(request, "This account is not registered as a recruiter.")
                    return redirect('users:recruiter_login')
                
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, f"Welcome back, {username}!")
                
                next_url = request.GET.get('next')
                if next_url and next_url.startswith('/'):
                    return redirect(next_url)
                return redirect('users:recruiter_dashboard')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
        # Add Bootstrap classes to form fields
        form.fields['username'].widget.attrs.update({'class': 'form-control'})
        form.fields['password'].widget.attrs.update({'class': 'form-control'})
    
    response = render(request, 'users/recruiter_login.html', {'form': form})
    response.set_cookie('csrftoken', get_token(request))
    return response

def send_verification_email(request, user, to_email):
    try:
        if not to_email:
            to_email = user.email
        
        if not to_email:
            raise ValueError("No email address provided")
            
        current_site = get_current_site(request)
        mail_subject = 'Activate your Worksy account'
        message = render_to_string('users/account_activation_email.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': account_activation_token.make_token(user),
            'protocol': 'https' if request.is_secure() else 'http'
        })

        # Use Django's send_mail instead of EmailMessage
        send_mail(
            subject=mail_subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,  # Use EMAIL_HOST_USER directly
            recipient_list=[to_email],
            fail_silently=False,
            html_message=message  # Include HTML version
        )
        
        print(f"Verification email sent to {to_email}")  # Add logging
        messages.success(request, f"Verification email sent to {to_email}. Please check your inbox and spam folder.")
        
    except Exception as e:
        print(f"Error sending verification email: {str(e)}")  # Add error logging
        messages.error(request, f"Error sending verification email: {str(e)}")
        raise  # Re-raise the exception for debugging

@ensure_csrf_cookie
def applicant_signup(request):
    # Set CSRF cookie
    get_token(request)
    
    if request.method == 'POST':
        form = ApplicantSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Deactivate account till it is verified
            user.save()
            
            # Set user role to applicant
            profile = UserProfile.objects.get(user=user)
            profile.role = 'APPLICANT'
            profile.save()
            
            # Send verification email
            send_verification_email(request, user, form.cleaned_data.get('email'))
            
            messages.success(request, 'Please confirm your email address to complete the registration.')
            return redirect('users:applicant_login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ApplicantSignupForm()
    
    response = render(request, 'users/applicant_signup.html', {'form': form})
    response.set_cookie('csrftoken', get_token(request))
    return response

@ensure_csrf_cookie
@csrf_protect
def recruiter_signup(request):
    if request.method == 'POST':
        form = RecruiterSignupForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.is_active = False  # Deactivate account till it is verified
                user.save()
                
                username = form.cleaned_data.get('username')
                company_name = form.cleaned_data.get('company_name')
                email = form.cleaned_data.get('email')
                
                # Set user role to recruiter
                profile = user.profile
                profile.role = 'RECRUITER'
                
                # Create company for the recruiter
                company = Company.objects.create(
                    name=company_name,
                    description=f"{company_name} description",
                    location="Location not specified"
                )
                
                # Associate company with user profile
                profile.company = company
                profile.save()
                
                # Send verification email
                send_verification_email(request, user, email)
                
                messages.success(request, 'Please confirm your email address to complete the registration.')
                return redirect('users:recruiter_login')
            except Exception as e:
                messages.error(request, f"Error creating account: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = RecruiterSignupForm()
    
    return render(request, 'users/recruiter_signup.html', {'form': form})

def activate_account(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and account_activation_token.check_token(user, token):
        # Ensure user has a profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Activate the user
        user.is_active = True
        user.save()
        
        # Log the user in with the specific backend
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, 'Thank you for confirming your email. Your account is now active!')
        
        # Redirect based on user role
        if profile.role == 'RECRUITER':
            return redirect('users:recruiter_dashboard')
        elif profile.role == 'APPLICANT':
            return redirect('users:applicant_dashboard')
        else:
            # If no role is set, set it to APPLICANT by default
            profile.role = 'APPLICANT'
            profile.save()
            return redirect('users:applicant_dashboard')
    else:
        messages.error(request, 'Activation link is invalid or has expired!')
        return redirect('users:home')

@login_required
def employer_dashboard(request):
    if not request.user.userprofile.is_employer:
        raise PermissionDenied("Only employers can access this page.")
    
    company = request.user.userprofile.company
    jobs = Job.objects.filter(company=company)
    recent_applications = JobApplication.objects.filter(job__company=company).order_by('-applied_at')[:5]
    
    context = {
        'jobs': jobs,
        'recent_applications': recent_applications,
    }
    return render(request, 'jobs/employer_dashboard.html', context)

@login_required
def applicant_dashboard(request):
    if request.user.profile.role != 'APPLICANT':
        messages.warning(request, 'You need to be a job seeker to access this page.')
        return redirect('role_selection')
    
    # Get applications
    applications = JobApplication.objects.filter(applicant=request.user)
    active_applications = applications.filter(
        status__in=['PENDING', 'REVIEWING', 'SHORTLISTED']
    ).order_by('-applied_date')
    
    past_applications = applications.filter(
        status__in=['REJECTED', 'ACCEPTED', 'WITHDRAWN']
    ).order_by('-applied_date')
    
    # Get recommended jobs for the user
    recommended_jobs = Job.objects.filter(is_active=True).order_by('-posted_date')[:5]
    
    # Get upcoming interviews
    interviews = Interview.objects.filter(
        application__applicant=request.user,
        scheduled_date__gte=timezone.now(),
        status='SCHEDULED'
    ).order_by('scheduled_date')
    
    # Calculate profile strength
    profile = request.user.profile
    profile_fields = ['bio', 'skills', 'experience', 'education', 'location', 'phone_number', 'resume']
    completed_fields = sum(1 for field in profile_fields if getattr(profile, field))
    profile_strength = int((completed_fields / len(profile_fields)) * 100)
    
    context = {
        'applications': applications,
        'active_applications': active_applications,
        'past_applications': past_applications,
        'recommendations': recommended_jobs,
        'interviews': interviews,
        'profile': profile,
        'profile_strength': profile_strength,
    }
    return render(request, 'users/applicant_dashboard.html', context)

@login_required
def recruiter_dashboard(request):
    # Check if user is a recruiter
    if request.user.profile.role != 'RECRUITER':
        messages.error(request, 'Access denied. This dashboard is for recruiters only.')
        return redirect('users:home')
    
    # Get jobs posted by the user's company
    jobs = Job.objects.filter(company=request.user.profile.company)
    
    # Get active jobs count
    active_jobs_count = jobs.filter(is_active=True).count()
    
    # Get applications for the user's company's jobs
    applications = JobApplication.objects.filter(job__company=request.user.profile.company)
    
    # Get pending applications count
    pending_applications_count = applications.filter(status='PENDING').count()
    
    # Get upcoming interviews
    interviews = Interview.objects.filter(
        application__job__company=request.user.profile.company,
        scheduled_date__gte=timezone.now(),
        status='SCHEDULED'
    ).order_by('scheduled_date')
    
    # Get recent applications
    recent_applications = applications.order_by('-applied_date')[:5]
    
    context = {
        'jobs': jobs,
        'active_jobs_count': active_jobs_count,
        'applications': applications,
        'pending_applications_count': pending_applications_count,
        'interviews': interviews,
        'recent_applications': recent_applications,
    }
    
    return render(request, 'users/recruiter_dashboard.html', context)

@login_required
def profile(request):
    user = request.user
    profile = user.profile
    applications = JobApplication.objects.filter(applicant=user) if user.profile.role == 'APPLICANT' else None
    
    context = {
        'user': user,
        'profile': profile,
        'applications': applications,
    }
    
    if user.profile.role == 'RECRUITER':
        return render(request, 'users/recruiter_profile.html', context)
    else:
        return render(request, 'users/profile.html', context)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        try:
            form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
            if form.is_valid():
                profile = form.save(commit=False)
                
                # Update user model fields if provided
                user = request.user
                first_name = request.POST.get('first_name')
                last_name = request.POST.get('last_name')
                email = request.POST.get('email')
                
                if first_name:
                    user.first_name = first_name
                if last_name:
                    user.last_name = last_name
                if email and email != user.email:
                    # Check if email is already taken
                    if User.objects.filter(email=email).exclude(id=user.id).exists():
                        messages.error(request, 'This email is already in use.')
                        return redirect('users:edit_profile')
                    user.email = email
                
                user.save()
                
                # Update profile fields with validation
                profile.bio = request.POST.get('bio', profile.bio)
                profile.location = request.POST.get('location', profile.location)
                
                # Validate phone number format
                phone_number = request.POST.get('phone_number')
                if phone_number:
                    # Remove any non-digit characters
                    phone_number = ''.join(filter(str.isdigit, phone_number))
                    if len(phone_number) < 10:
                        messages.error(request, 'Please enter a valid phone number.')
                        return redirect('users:edit_profile')
                profile.phone_number = phone_number
                
                profile.skills = request.POST.get('skills', profile.skills)
                profile.experience = request.POST.get('experience', profile.experience)
                profile.education = request.POST.get('education', profile.education)
                
                # Validate URL fields
                linkedin_profile = request.POST.get('linkedin_profile')
                if linkedin_profile and not linkedin_profile.startswith(('http://', 'https://')):
                    linkedin_profile = f'https://{linkedin_profile}'
                profile.linkedin_profile = linkedin_profile

                github_profile = request.POST.get('github_profile')
                if github_profile and not github_profile.startswith(('http://', 'https://')):
                    github_profile = f'https://{github_profile}'
                profile.github_profile = github_profile

                website = request.POST.get('website')
                if website and not website.startswith(('http://', 'https://')):
                    website = f'https://{website}'
                profile.website = website
                
                # Handle file uploads with validation
                if 'profile_picture' in request.FILES:
                    image = request.FILES['profile_picture']
                    # Validate file type
                    if not image.content_type.startswith('image/'):
                        messages.error(request, 'Please upload a valid image file.')
                        return redirect('users:edit_profile')
                    # Validate file size (max 5MB)
                    if image.size > 5 * 1024 * 1024:
                        messages.error(request, 'Profile picture must be less than 5MB.')
                        return redirect('users:edit_profile')
                    profile.profile_picture = image

                if 'resume' in request.FILES:
                    resume = request.FILES['resume']
                    # Validate file type
                    allowed_types = ['application/pdf', 'application/msword', 
                                   'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
                    if resume.content_type not in allowed_types:
                        messages.error(request, 'Please upload a PDF or Word document.')
                        return redirect('users:edit_profile')
                    # Validate file size (max 10MB)
                    if resume.size > 10 * 1024 * 1024:
                        messages.error(request, 'Resume must be less than 10MB.')
                        return redirect('users:edit_profile')
                    profile.resume = resume
                
                profile.save()
                
                # Update company information if user is a recruiter
                if request.user.profile.role == 'RECRUITER':
                    company = request.user.profile.company
                    if company:
                        try:
                            company.name = request.POST.get('company_name', company.name)
                            company.mission = request.POST.get('company_mission', company.mission)
                            company.vision = request.POST.get('company_vision', company.vision)
                            company.about = request.POST.get('company_about', company.about)
                            company.address = request.POST.get('company_address', company.address)
                            company.careers = request.POST.get('company_careers', company.careers)
                            
                            # Handle company logo upload
                            if 'company_logo' in request.FILES:
                                logo = request.FILES['company_logo']
                                # Validate file type
                                if not logo.content_type.startswith('image/'):
                                    messages.error(request, 'Please upload a valid image file for company logo.')
                                    return redirect('users:edit_profile')
                                # Validate file size (max 5MB)
                                if logo.size > 5 * 1024 * 1024:
                                    messages.error(request, 'Company logo must be less than 5MB.')
                                    return redirect('users:edit_profile')
                                company.logo = logo
                            
                            company.save()
                        except Exception as e:
                            messages.warning(request, f'Profile updated but company information could not be saved: {str(e)}')
                            return redirect('users:profile')
                
                messages.success(request, 'Your profile has been updated successfully!')
                return redirect('users:profile')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        except Exception as e:
            messages.error(request, f'An error occurred while updating your profile: {str(e)}')
            return redirect('users:edit_profile')
    else:
        form = UserProfileForm(instance=request.user.profile)
    
    context = {
        'form': form,
        'user': request.user,
        'profile': request.user.profile
    }
    return render(request, 'users/edit_profile.html', context)

@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        user.delete()
        return redirect('/')  # Redirect to home after account deletion
    return render(request, 'users/delete_account.html')

@login_required
def notifications(request):
    # Get all notifications for the user
    user_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Mark all as read
    unread_notifications = user_notifications.filter(is_read=False)
    for notification in unread_notifications:
        notification.is_read = True
        notification.save()
    
    context = {
        'notifications': user_notifications,
    }
    return render(request, 'users/notifications.html', context)

@login_required
def message_list(request):
    # Get all conversations for the user
    conversations = Conversation.objects.filter(participants=request.user).order_by('-updated_at')
    
    # Add other user information to each conversation
    conversations_with_other_user = []
    for conversation in conversations:
        other_user = conversation.participants.exclude(id=request.user.id).first()
        conversations_with_other_user.append({
            'conversation': conversation,
            'other_user': other_user
        })
    
    context = {
        'conversations_with_other_user': conversations_with_other_user,
    }
    return render(request, 'users/message_list.html', context)

@login_required
def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    messages_list = conversation.messages.all().order_by('created_at')
    
    # Get the other participant
    other_participant = conversation.participants.exclude(id=request.user.id).first()
    
    # Mark messages as read
    unread_messages = messages_list.filter(is_read=False).exclude(sender=request.user)
    for message in unread_messages:
        message.is_read = True
        message.save()
    
    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            content = form.cleaned_data['content']
            
            # Create new message
            new_message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=content
            )
            
            # Update conversation timestamp
            conversation.save()  # This will update the updated_at field
            
            # Create notification for the other participant
            if other_participant:
                Notification.objects.create(
                    user=other_participant,
                    notification_type='MESSAGE',
                    title='New Message',
                    message=f'You have a new message from {request.user.username}',
                    link=f'/users/messages/{conversation.id}/'
                )
            
            return redirect('users:conversation_detail', conversation_id=conversation.id)
    else:
        form = MessageForm()
    
    context = {
        'conversation': conversation,
        'messages': messages_list,
        'other_participant': other_participant,
        'form': form,
    }
    return render(request, 'users/conversation_detail.html', context)

@login_required
def start_conversation(request, username):
    User = get_user_model()
    try:
        # Try to get user by username first
        other_user = User.objects.filter(username=username).first()
        
        # If not found by username, try to get by ID if username is numeric
        if not other_user and username.isdigit():
            other_user = User.objects.filter(id=username).first()
        
        if not other_user:
            messages.error(request, "User not found.")
            return redirect('users:home')
        
        # Don't allow starting conversation with yourself
        if request.user == other_user:
            messages.error(request, "You cannot start a conversation with yourself.")
            return redirect('users:public_profile', username=other_user.username)
        
        # Check if conversation already exists
        conversation = Conversation.objects.filter(participants=request.user).filter(participants=other_user).first()
        
        if not conversation:
            # Create new conversation
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, other_user)
            
            # Add initial message if provided
            if request.POST.get('message'):
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    content=request.POST.get('message')
                )
            
            messages.success(request, f"Started a new conversation with {other_user.get_full_name() or other_user.username}")
        
        return redirect('users:conversation_detail', conversation_id=conversation.id)
    
    except Exception as e:
        messages.error(request, "An error occurred while starting the conversation. Please try again.")
        return redirect('users:home')

@login_required
def public_profile(request, username):
    user = get_object_or_404(User, username=username)
    profile = user.profile
    
    context = {
        'profile_user': user,
        'profile': profile,
    }
    return render(request, 'users/public_profile.html', context)

def search_users(request):
    """Search for users by username, name, or skills"""
    query = request.GET.get('q', '')
    
    if query:
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(profile__skills__icontains=query)
        ).distinct()
    else:
        users = User.objects.none()
    
    context = {
        'users': users,
        'query': query
    }
    return render(request, 'users/search_users.html', context)

# Chatbot views
@login_required
def chatbot(request):
    # Get all chatbot conversations for the user
    conversations = ChatbotConversation.objects.filter(user=request.user)
    
    # Get or create active conversation
    active_conversation_id = request.session.get('active_chatbot_conversation')
    active_conversation = None
    
    if active_conversation_id:
        try:
            active_conversation = ChatbotConversation.objects.get(id=active_conversation_id, user=request.user)
            
            # Clean up duplicate messages
            messages = ChatbotMessage.objects.filter(conversation=active_conversation).order_by('created_at')
            last_message = None
            for message in messages:
                if last_message and message.content == last_message.content and \
                   message.message_type == last_message.message_type and \
                   (message.created_at - last_message.created_at).total_seconds() < 5:
                    # Delete duplicate message
                    message.delete()
                else:
                    last_message = message
                    
        except ChatbotConversation.DoesNotExist:
            active_conversation = None
    
    if not active_conversation and conversations.exists():
        active_conversation = conversations.first()
    elif not active_conversation:
        # Create a new conversation
        active_conversation = ChatbotConversation.objects.create(
            user=request.user,
            title="Resume Help"
        )
        
        # Add welcome message
        ChatbotMessage.objects.create(
            conversation=active_conversation,
            message_type='BOT',
            content="Hello! I'm your AI resume assistant. I can help you improve your resume, prepare for interviews, or answer questions about job applications. How can I help you today?"
        )
    
    # Set active conversation in session
    request.session['active_chatbot_conversation'] = active_conversation.id
    
    # Get messages for active conversation (after cleanup)
    messages = ChatbotMessage.objects.filter(conversation=active_conversation).order_by('created_at')
    
    context = {
        'conversations': conversations,
        'active_conversation': active_conversation,
        'messages': messages,
        'form': ChatbotMessageForm(),
    }
    return render(request, 'users/chatbot.html', context)

@login_required
def new_chatbot_conversation(request):
    # Create a new conversation
    conversation = ChatbotConversation.objects.create(
        user=request.user,
        title="New Conversation"
    )
    
    # Add welcome message
    ChatbotMessage.objects.create(
        conversation=conversation,
        message_type='BOT',
        content="Hello! I'm your AI resume assistant. I can help you improve your resume, prepare for interviews, or answer questions about job applications. How can I help you today?"
    )
    
    # Set as active conversation
    request.session['active_chatbot_conversation'] = conversation.id
    
    return redirect('users:chatbot')

@login_required
def select_chatbot_conversation(request, conversation_id):
    conversation = get_object_or_404(ChatbotConversation, id=conversation_id, user=request.user)
    request.session['active_chatbot_conversation'] = conversation.id
    return redirect('users:chatbot')

@login_required
@require_POST
def send_chatbot_message(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        conversation_id = request.session.get('active_chatbot_conversation')
        if not conversation_id:
            return JsonResponse({'error': 'No active conversation'}, status=400)
        
        try:
            conversation = ChatbotConversation.objects.get(id=conversation_id, user=request.user)
            
            # Get the last message timestamp from the session
            last_message_time = request.session.get('last_message_time', 0)
            current_time = timezone.now().timestamp()
            
            # Prevent duplicate messages within 2 seconds
            if current_time - last_message_time < 2:
                return JsonResponse({'error': 'Please wait a moment'}, status=429)
            
            # Update last message timestamp
            request.session['last_message_time'] = current_time
            
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            
            if not user_message:
                return JsonResponse({'error': 'Message cannot be empty'}, status=400)
            
            # Save user message without creating a notification
            user_message_obj = ChatbotMessage.objects.create(
                conversation=conversation,
                message_type='USER',
                content=user_message
            )
            
            try:
                # Generate bot response based on user message
                bot_response = generate_chatbot_response(user_message, request.user)
                
                # Save bot response without creating a notification
                bot_message = ChatbotMessage.objects.create(
                    conversation=conversation,
                    message_type='BOT',
                    content=bot_response
                )
                
                # Update conversation title silently
                if conversation.title == "New Conversation":
                    conversation.title = user_message[:30] + "..." if len(user_message) > 30 else user_message
                    conversation.save(update_fields=['title'])
                
                # Update conversation timestamp silently
                conversation.updated_at = bot_message.created_at
                conversation.save(update_fields=['updated_at'])
                
                return JsonResponse({
                    'user_message': {
                        'content': user_message,
                        'created_at': user_message_obj.created_at.strftime('%b %d, %Y, %I:%M %p')
                    },
                    'bot_message': {
                        'content': bot_response,
                        'created_at': bot_message.created_at.strftime('%b %d, %Y, %I:%M %p')
                    }
                })
                
            except Exception as e:
                print(f"Error generating chatbot response: {str(e)}")
                return JsonResponse({'error': str(e)}, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid message format'}, status=400)
        except Exception as e:
            print(f"Error processing chatbot message: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

def generate_chatbot_response(user_message, user):
    """Generate a response from the chatbot using OpenAI API"""
    import openai
    import os
    from django.conf import settings
    
    # Get OpenAI API key from environment variables
    api_key = os.environ.get('OPENAI_API_KEY')
    
    if not api_key:
        print("OpenAI API key not found in environment variables")
        return "I'm your AI resume assistant, but I'm currently experiencing some technical difficulties. Please try again later or contact support."
    
    try:
        # Set up OpenAI client with just the API key
        client = openai.OpenAI(api_key=api_key)
        
        # Get user profile information to provide context
        profile = user.profile
        profile_info = {
            "has_resume": bool(profile.resume),
            "has_skills": bool(profile.skills),
            "has_experience": bool(profile.experience),
            "has_education": bool(profile.education),
            "role": profile.role
        }
        
        # Create system message with context
        system_message = f"""
        You are an AI resume and job search assistant for a job portal. 
        Your goal is to help users improve their resumes, prepare for interviews, and enhance their job search strategies.
        
        User profile information:
        - Has uploaded resume: {profile_info['has_resume']}
        - Has listed skills: {profile_info['has_skills']}
        - Has listed experience: {profile_info['has_experience']}
        - Has listed education: {profile_info['has_education']}
        - Role on platform: {profile_info['role']}
        
        Provide helpful, concise advice tailored to the user's needs. If they haven't completed their profile,
        encourage them to do so for better job matching.
        """
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        # Extract and return the response text
        return response.choices[0].message.content
        
    except openai.AuthenticationError as e:
        print(f"OpenAI Authentication Error: {str(e)}")
        return "I'm having trouble authenticating with the AI service. Please contact support."
    except openai.APIError as e:
        print(f"OpenAI API Error: {str(e)}")
        return "I'm having trouble connecting to the AI service. Please try again later."
    except Exception as e:
        print(f"Unexpected error in generate_chatbot_response: {str(e)}")
        return "I'm experiencing some technical difficulties. Please try again later."

@login_required
def logout_view(request):
    """
    Handle logout with confirmation page
    """
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have been successfully logged out.')
        return redirect('users:home')
    return render(request, 'users/logout.html')

def github_login(request):
    """
    Display the GitHub login page
    """
    return render(request, 'users/github_login.html')

def oauth_login(request):
    """
    Display the unified OAuth login page and handle OAuth authentication
    """
    if request.user.is_authenticated:
        # If user is already logged in, redirect based on role
        if request.user.profile.role == 'APPLICANT':
            return redirect('users:applicant_dashboard')
        elif request.user.profile.role == 'RECRUITER':
            return redirect('users:recruiter_dashboard')
        else:
            # If no role is set, redirect to role selection
            return redirect('users:role_selection')
    
    return render(request, 'users/oauth_login.html')

def social_auth_role_handler(backend, user, response, *args, **kwargs):
    """
    Handle role selection for social auth users
    """
    if not hasattr(user, 'profile'):
        # Default to applicant role for social auth users
        profile = UserProfile.objects.create(
            user=user,
            role='APPLICANT'  # <-- This is the issue
        )

def test_email(request):
    if not request.user.is_authenticated:
        return HttpResponse("Please log in first")
    
    try:
        # First, print email settings for debugging
        print(f"Email Settings:")
        print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
        print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
        print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
        print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
        print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        
        # Send test email
        subject = 'Test Email from Worksy'
        message = f"""
        This is a test email to verify the email configuration.
        Sent to: {request.user.email}
        From: {settings.EMAIL_HOST_USER}
        Time: {timezone.now()}
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[request.user.email],
            fail_silently=False,
        )
        
        return HttpResponse(
            f"Test email sent successfully!<br><br>"
            f"Sent to: {request.user.email}<br>"
            f"From: {settings.EMAIL_HOST_USER}<br>"
            f"Please check both your inbox and spam folder."
        )
    except Exception as e:
        error_message = f"Error sending email: {str(e)}"
        print(error_message)  # Print to console for debugging
        return HttpResponse(f"Error: {error_message}")

