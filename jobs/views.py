import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.http import JsonResponse
from .models import Job, JobApplication, Company, JobCategory
from .forms import JobSearchForm, JobApplicationForm, JobPostForm
from django.db.models import Count
from django.utils import timezone
from .models import Interview
from django.urls import reverse
from datetime import timedelta
from notifications.models import Notification
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_datetime
from django.core.exceptions import PermissionDenied


def home(request):
    # Show the home page for all users
    featured_jobs = Job.objects.filter(is_active=True).order_by('-posted_date')[:6]
    job_categories = JobCategory.objects.all()
    
    context = {
        'featured_jobs': featured_jobs,
        'job_categories': job_categories,
    }
    return render(request, 'jobs/home.html', context)

def job_list(request):
    form = JobSearchForm(request.GET)
    jobs = Job.objects.filter(is_active=True)
    
    if form.is_valid():
        keyword = form.cleaned_data.get('keyword')
        location = form.cleaned_data.get('location')
        category = form.cleaned_data.get('category')
        job_type = form.cleaned_data.get('job_type')
        experience_level = form.cleaned_data.get('experience_level')
        salary_min = form.cleaned_data.get('salary_min')
        salary_max = form.cleaned_data.get('salary_max')
        posted_within = form.cleaned_data.get('posted_within')
        
        # Basic search filters
        if keyword:
            jobs = jobs.filter(
                Q(title__icontains=keyword) | 
                Q(description__icontains=keyword) |
                Q(skills_required__icontains=keyword) |
                Q(company__name__icontains=keyword)
            )
        
        if location:
            jobs = jobs.filter(location__icontains=location)
        
        if category:
            jobs = jobs.filter(category=category)
        
        if job_type:
            jobs = jobs.filter(job_type=job_type)
        
        # Advanced search filters
        if experience_level:
            jobs = jobs.filter(experience_level=experience_level)
        
        if salary_min:
            jobs = jobs.filter(salary_min__gte=salary_min)
        
        if salary_max:
            jobs = jobs.filter(salary_max__lte=salary_max)
        
        if posted_within:
            days = int(posted_within)
            date_threshold = timezone.now() - timedelta(days=days)
            jobs = jobs.filter(posted_date__gte=date_threshold)
    
    # Default sorting by most recent
    jobs = jobs.order_by('-posted_date')
    
    paginator = Paginator(jobs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'page_obj': page_obj,
    }
    return render(request, 'jobs/job_list.html', context)

def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id, is_active=True)
    related_jobs = Job.objects.filter(
        category=job.category, 
        is_active=True
    ).exclude(id=job.id)[:3]
    
    # Check if user has already applied
    has_applied = False
    user_role = None
    if request.user.is_authenticated:
        has_applied = JobApplication.objects.filter(job=job, applicant=request.user).exists()
        user_role = request.user.profile.role if hasattr(request.user, 'profile') else None
    
    context = {
        'job': job,
        'related_jobs': related_jobs,
        'has_applied': has_applied,
        'user_role': user_role,
    }
    return render(request, 'jobs/job_detail.html', context)

@login_required
def apply_for_job(request, job_id):
    job = get_object_or_404(Job, id=job_id, is_active=True)
    
    # Check if already applied
    if JobApplication.objects.filter(job=job, applicant=request.user).exists():
        messages.warning(request, 'You have already applied for this job.')
        return redirect('jobs:job_detail', job_id=job.id)
    
    if request.method == 'POST':
        # Check if using profile resume
        use_profile_resume = request.POST.get('use_profile_resume') == 'on'
        
        # Create a copy of POST data to modify
        post_data = request.POST.copy()
        files_data = request.FILES.copy()
        
        # If using profile resume and it exists
        if use_profile_resume and request.user.profile.resume:
            # Remove resume from required fields
            post_data['resume'] = ''
        elif not use_profile_resume and not request.FILES.get('resume'):
            messages.error(request, 'Please upload a resume.')
            return render(request, 'jobs/apply_job.html', {
                'form': JobApplicationForm(),
                'job': job
            })
        
        form = JobApplicationForm(post_data, files_data)
        
        # If using profile resume, make the field not required
        if use_profile_resume:
            form.fields['resume'].required = False
        
        if form.is_valid():
            try:
                application = form.save(commit=False)
                application.job = job
                application.applicant = request.user
                
                # Set resume from profile if using profile resume
                if use_profile_resume:
                    from django.core.files import File
                    application.resume = request.user.profile.resume
                
                application.save()
                
                # Create notification for job poster
                Notification.objects.create(
                    user=job.posted_by,
                    notification_type='NEW_APPLICATION',
                    title='New Job Application',
                    message=f'{request.user.get_full_name() or request.user.username} has applied for {job.title}',
                    link=f'/jobs/{job.id}/'
                )
                
                messages.success(request, 'Your application has been submitted successfully!')
                return redirect('jobs:job_detail', job_id=job.id)
            except Exception as e:
                print(f"Error submitting application: {str(e)}")  # For debugging
                messages.error(request, 'There was an error submitting your application. Please try again.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = JobApplicationForm()
    
    context = {
        'form': form,
        'job': job,
    }
    return render(request, 'jobs/apply_job.html', context)

@login_required
def post_job(request):
    # Check if user is a recruiter
    if request.user.profile.role != 'RECRUITER' and not request.user.is_staff:
        messages.warning(request, 'You need to be a recruiter to post jobs.')
        return redirect('users:profile')  # Redirect to profile page instead of role_selection
    
    if request.method == 'POST':
        form = JobPostForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.posted_by = request.user
            job.company = request.user.profile.company  # Set the company from the user's profile
            job.save()
            
            # If AJAX request, return JSON response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'job': {
                        'id': job.id,
                        'title': job.title,
                        'company_name': job.company.name,
                        'job_type_display': job.get_job_type_display(),
                        'location': job.location,
                        'url': reverse('jobs:job_detail', args=[job.id])
                    }
                })
            
            messages.success(request, 'Job posted successfully!')
            return redirect('jobs:job_detail', job_id=job.id)
    else:
        form = JobPostForm()
    
    context = {
        'form': form,
    }
    return render(request, 'jobs/post_job.html', context)

@login_required
def my_jobs(request):
    # Check if user is a recruiter
    if request.user.profile.role != 'RECRUITER' and not request.user.is_staff:
        messages.warning(request, 'You need to be a recruiter to access this page.')
        return redirect('users:profile')  # Redirect to profile page instead of role_selection
    
    posted_jobs = Job.objects.filter(posted_by=request.user)
    applications = JobApplication.objects.filter(applicant=request.user)
    
    context = {
        'posted_jobs': posted_jobs,
        'applications': applications,
    }
    return render(request, 'jobs/my_jobs.html', context)

@login_required
def application_dashboard(request):
    # Check if user is an applicant
    if request.user.profile.role != 'APPLICANT' and not request.user.is_staff:
        messages.warning(request, 'You need to be a job seeker to access this page.')
        return redirect('users:profile')  # Redirect to profile page instead of role_selection
    
    # Get all applications for the user
    applications = JobApplication.objects.filter(applicant=request.user)
    
    # Group by status
    pending = applications.filter(status='PENDING')
    reviewing = applications.filter(status='REVIEWING')
    shortlisted = applications.filter(status='SHORTLISTED')
    accepted = applications.filter(status='ACCEPTED')
    rejected = applications.filter(status='REJECTED')
    
    # Get upcoming interviews
    interviews = Interview.objects.filter(
        application__applicant=request.user,
        scheduled_date__gte=timezone.now(),
        status='SCHEDULED'
    ).order_by('scheduled_date')
    
    context = {
        'applications': applications,
        'pending': pending,
        'reviewing': reviewing,
        'shortlisted': shortlisted,
        'accepted': accepted,
        'rejected': rejected,
        'interviews': interviews,
    }
    return render(request, 'jobs/application_dashboard.html',context)
@login_required
def employer_dashboard(request):
    # Check if user is a recruiter
    if request.user.profile.role != 'RECRUITER' and not request.user.is_staff:
        messages.warning(request, 'You need to be a recruiter to access this page.')
        return redirect('users:profile')  # Redirect to profile page instead of role_selection
    
    # Get jobs posted by the user
    jobs = Job.objects.filter(posted_by=request.user)
    
    # Get active jobs count
    active_jobs_count = jobs.filter(is_active=True).count()
    
    # Get applications for those jobs
    applications = JobApplication.objects.filter(job__in=jobs)
    
    # Get pending applications count
    pending_applications_count = applications.filter(status='PENDING').count()
    
    # Get recent applications
    recent_applications = applications.order_by('-applied_date')[:10]
    
    # Get upcoming interviews
    interviews = Interview.objects.filter(
        application__job__posted_by=request.user,
        scheduled_date__gte=timezone.now(),
        status='SCHEDULED'
    ).order_by('scheduled_date')
    
    context = {
        'jobs': jobs,
        'active_jobs_count': active_jobs_count,
        'applications': applications,
        'pending_applications_count': pending_applications_count,
        'recent_applications': recent_applications,
        'interviews': interviews,
    }
    return render(request, 'jobs/employer_dashboard.html', context)

@login_required
@require_POST
def update_application_status(request):
    try:
        # Try to get data from POST first, then try JSON
        application_id = request.POST.get('application_id')
        new_status = request.POST.get('status')
        
        # If not in POST, try JSON
        if not application_id or not new_status:
            try:
                data = json.loads(request.body)
                application_id = data.get('application_id')
                new_status = data.get('status')
            except json.JSONDecodeError:
                pass
        
        if not application_id or not new_status:
            return JsonResponse({
                'success': False,
                'error': 'Application ID and status are required'
            }, status=400)
        
        # Get the application and verify permissions
        application = get_object_or_404(JobApplication, 
            id=application_id,
            job__posted_by=request.user
        )
        
        # Validate the status
        valid_statuses = dict(JobApplication.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            return JsonResponse({
                'success': False,
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }, status=400)
        
        # Update the status
        application.status = new_status
        application.save()
        
        # Create notification for the applicant
        status_display = dict(JobApplication.STATUS_CHOICES)[new_status]
        Notification.objects.create(
            user=application.applicant,
            notification_type='APPLICATION_STATUS_UPDATED',
            title='Application Status Updated',
            message=f'Your application for {application.job.title} has been {status_display}',
            link=f'/jobs/application-dashboard/'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Application status updated successfully',
            'new_status': new_status,
            'status_display': status_display
        })
        
    except Exception as e:
        import traceback
        print("Error updating application status:", str(e))
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
@require_POST
def schedule_interview(request):
    try:
        # Get and validate application_id
        application_id = request.POST.get('application_id')
        if not application_id:
            return JsonResponse({
                'success': False,
                'error': 'Application ID is required'
            }, status=400)
        
        # Get and validate the application
        try:
            application = JobApplication.objects.get(
                id=application_id,
                job__posted_by=request.user
            )
        except JobApplication.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Application not found or you do not have permission to schedule an interview'
            }, status=404)
        
        # Get and validate scheduled_date
        scheduled_date_str = request.POST.get('scheduled_date')
        if not scheduled_date_str:
            return JsonResponse({
                'success': False,
                'error': 'Scheduled date is required'
            }, status=400)
        
        # Parse and validate the datetime
        try:
            from datetime import datetime
            
            # Parse the datetime string from datetime-local format
            try:
                scheduled_date = datetime.strptime(scheduled_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid datetime format. Please use the datetime picker.'
                }, status=400)
            
            # Make the datetime timezone-aware using Django's timezone utilities
            scheduled_date = timezone.make_aware(scheduled_date)
            
            # Get current time (already timezone-aware)
            current_time = timezone.now()
            
            # Compare datetimes
            if scheduled_date <= current_time:
                return JsonResponse({
                    'success': False,
                    'error': 'Interview must be scheduled for a future date'
                }, status=400)
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format: {str(e)}'
            }, status=400)
        
        # Get other fields with defaults
        try:
            duration_minutes = int(request.POST.get('duration_minutes', '30'))
            if duration_minutes < 15:
                return JsonResponse({
                    'success': False,
                    'error': 'Duration must be at least 15 minutes'
                }, status=400)
        except ValueError:
            duration_minutes = 30
        
        is_virtual = request.POST.get('is_virtual') == 'on'
        meeting_link = request.POST.get('meeting_link') if is_virtual else None
        location = request.POST.get('location') if not is_virtual else None
        notes = request.POST.get('notes', '')
        
        # First update application status
        try:
            # Update application status to SHORTLISTED
            application.status = 'SHORTLISTED'
            application.save()
        except Exception as e:
            print("Error updating application status:", str(e))
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'error': f'Error updating application status: {str(e)}'
            }, status=400)
        
        # Create the interview
        interview = Interview.objects.create(
            application=application,
            scheduled_date=scheduled_date,
            duration_minutes=duration_minutes,
            is_virtual=is_virtual,
            meeting_link=meeting_link,
            location=location,
            notes=notes,
            status='SCHEDULED'
        )
        
        # Create notification for the applicant
        Notification.objects.create(
            user=application.applicant,
            notification_type='INTERVIEW_SCHEDULED',
            title='Interview Scheduled',
            message=f'Your application for {application.job.title} has been shortlisted and an interview has been scheduled.',
            link=reverse('jobs:interview_detail', args=[interview.id])
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Interview scheduled successfully',
            'interview': {
                'id': interview.id,
                'scheduled_date': interview.scheduled_date.isoformat(),
                'is_virtual': interview.is_virtual,
                'location': interview.location,
                'meeting_link': interview.meeting_link
            }
        })
        
    except Exception as e:
        import traceback
        print("Error scheduling interview:", str(e))
        print(traceback.format_exc())  # Print full traceback for debugging
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def interview_detail(request, interview_id):
    try:
        # Get the interview
        interview = get_object_or_404(Interview, id=interview_id)
        
        # Check if user has permission to view this interview
        if not (interview.application.job.posted_by == request.user or 
                interview.application.applicant == request.user):
            return JsonResponse({
                'success': False,
                'error': 'You do not have permission to view this interview'
            }, status=403)
        
        # Check if request wants JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Format the data for JSON response
            data = {
                'success': True,
                'interview': {
                    'id': interview.id,
                    'job_title': interview.application.job.title,
                    'company_name': interview.application.job.company.name,
                    'applicant_name': interview.application.applicant.get_full_name() or interview.application.applicant.username,
                    'scheduled_date': interview.scheduled_date.strftime('%B %d, %Y at %I:%M %p'),
                    'duration_minutes': interview.duration_minutes,
                    'is_virtual': interview.is_virtual,
                    'meeting_link': interview.meeting_link,
                    'location': interview.location,
                    'notes': interview.notes,
                    'status': interview.status
                }
            }
            return JsonResponse(data)
        
        # For non-AJAX requests, redirect to appropriate dashboard
        if interview.application.job.posted_by == request.user:
            return redirect('jobs:employer_dashboard')
        else:
            return redirect('users:application_dashboard')
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=404)

@login_required
@login_required
@require_POST
def delete_job(request, job_id):
    try:
        job = get_object_or_404(Job, id=job_id, posted_by=request.user)
        job.delete()
        return JsonResponse({
            'success': True,
            'message': 'Job posting deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def view_job_applications(request, job_id):
    try:
        job = get_object_or_404(Job, id=job_id, posted_by=request.user)
        applications = JobApplication.objects.filter(job=job).select_related('applicant')
        
        applications_data = [{
            'id': app.id,
            'applicant_name': app.applicant.get_full_name() or app.applicant.username,
            'applicant_username': app.applicant.username,
            'applied_date': app.applied_date.strftime('%B %d, %Y'),
            'status': app.status,
            'resume_url': app.resume.url if app.resume else None
        } for app in applications]
        
        return JsonResponse({
            'success': True,
            'applications': applications_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

def edit_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check if user is authorized to edit this job
    if job.posted_by != request.user and not request.user.is_staff:
        raise PermissionDenied("You don't have permission to edit this job.")
    
    if request.method == 'POST':
        form = JobPostForm(request.POST, instance=job)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Job updated successfully!')
                return redirect('jobs:job_detail', job_id=job.id)
            except Exception as e:
                messages.error(request, f'Error updating job: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = JobPostForm(instance=job)
    
    context = {
        'form': form,
        'job': job,
    }
    return render(request, 'jobs/edit_job.html', context)