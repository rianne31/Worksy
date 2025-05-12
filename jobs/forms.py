from django import forms
from .models import Job, JobApplication, JobCategory, Interview
from django.utils import timezone
from datetime import timedelta
import os

class JobSearchForm(forms.Form):
    keyword = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job title, keywords, or company'})
    )
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location'})
    )
    category = forms.ModelChoiceField(
        queryset=JobCategory.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    job_type = forms.ChoiceField(
        choices=[('', 'All Types')] + list(Job.JOB_TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    experience_level = forms.ChoiceField(
        choices=[('', 'Any Experience')] + list(Job.EXPERIENCE_LEVEL_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    salary_min = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Min Salary'})
    )
    salary_max = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Max Salary'})
    )
    posted_within = forms.ChoiceField(
        choices=[
            ('', 'Any Time'),
            ('1', 'Last 24 Hours'),
            ('7', 'Last Week'),
            ('30', 'Last Month'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = ['resume', 'cover_letter']
        widgets = {
            'resume': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx'
            }),
            'cover_letter': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Write your cover letter here...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cover_letter'].required = True
        self.fields['resume'].required = True
        
    def clean_resume(self):
        resume = self.cleaned_data.get('resume')
        if resume:
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx']
            ext = os.path.splitext(resume.name)[1].lower()
            if ext not in allowed_extensions:
                raise forms.ValidationError('Only PDF, DOC, and DOCX files are allowed.')
            # Check file size (max 5MB)
            if resume.size > 5 * 1024 * 1024:
                raise forms.ValidationError('File size must be under 5MB.')
        return resume

class JobPostForm(forms.ModelForm):
    class Meta:
        model = Job
        exclude = ['posted_by', 'is_active', 'posted_date', 'company']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'responsibilities': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'salary_min': forms.NumberInput(attrs={'class': 'form-control'}),
            'salary_max': forms.NumberInput(attrs={'class': 'form-control'}),
            'job_type': forms.Select(attrs={'class': 'form-select'}),
            'experience_level': forms.Select(attrs={'class': 'form-select'}),
            'skills_required': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter skills separated by commas'}),
            'deadline': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

class InterviewScheduleForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = ['scheduled_date', 'duration_minutes', 'location', 'meeting_link', 'is_virtual', 'notes']
        widgets = {
            'scheduled_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'meeting_link': forms.URLInput(attrs={'class': 'form-control'}),
            'is_virtual': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }