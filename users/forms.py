from django import forms
from .models import UserProfile
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=False)
    company_name = forms.CharField(max_length=100, required=False)
    company_mission = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=False)
    company_vision = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=False)
    company_about = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=False)
    company_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    company_careers = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=False)
    
    class Meta:
        model = UserProfile
        fields = [
            'bio', 'profile_picture', 'resume', 'skills', 
            'experience', 'education', 'location', 'phone_number',
            'linkedin_profile', 'github_profile', 'website'
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'skills': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Enter skills separated by commas'}),
            'experience': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'education': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'linkedin_profile': forms.URLInput(attrs={'class': 'form-control'}),
            'github_profile': forms.URLInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            
            # Set company fields if user is an employer
            if self.instance.role == 'RECRUITER' and self.instance.company:
                self.fields['company_name'].initial = self.instance.company.name
                self.fields['company_mission'].initial = self.instance.company.mission
                self.fields['company_vision'].initial = self.instance.company.vision
                self.fields['company_about'].initial = self.instance.company.about
                self.fields['company_address'].initial = self.instance.company.address
                self.fields['company_careers'].initial = self.instance.company.careers

class MessageForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Type your message here...'}),
        label=''
    )

class ChatbotMessageForm(forms.Form):
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3, 
            'class': 'form-control', 
            'placeholder': 'Ask me about resume help, interview tips, or job search advice...',
            'id': 'chatbot-message-input'
        }),
        label='',
        required=True
    )

class RecruiterSignupForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    company_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your company name'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'company_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Create UserProfile if it doesn't exist
            UserProfile.objects.get_or_create(user=user)
        return user

class ApplicantSignupForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Create UserProfile if it doesn't exist
            UserProfile.objects.get_or_create(user=user)
        return user

