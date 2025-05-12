from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from jobs.models import Company, JobCategory, Job
from django.utils import timezone

class Command(BaseCommand):
    help = 'Sets up initial test data'

    def handle(self, *args, **kwargs):
        # Create a test company
        company = Company.objects.create(
            name='Tech Corp',
            description='A leading technology company',
            location='New York, NY',
        )
        self.stdout.write(self.style.SUCCESS('Created test company'))

        # Create job categories
        categories = [
            'Software Development',
            'Data Science',
            'Design',
            'Marketing',
            'Information Technology',
            'Human Resources',
            'Sales',
            'Finance',
            'Customer Service',
            'Administration',
            
        ]
        for cat_name in categories:
            JobCategory.objects.create(name=cat_name)
        self.stdout.write(self.style.SUCCESS('Created job categories'))

        # Get the first user (superuser)
        user = User.objects.first()
        category = JobCategory.objects.first()

        # Create a test job
        Job.objects.create(
            title='Senior Software Engineer',
            company=company,
            category=category,
            description='We are looking for a senior software engineer',
            requirements='5+ years of experience',
            responsibilities='Lead development projects',
            location='New York, NY',
            job_type='FULL_TIME',
            experience_level='SENIOR',
            skills_required='Python, Django, JavaScript',
            posted_by=user,
            posted_date=timezone.now(),
        )
        self.stdout.write(self.style.SUCCESS('Created test job')) 