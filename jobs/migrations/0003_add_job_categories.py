from django.db import migrations

def add_job_categories(apps, schema_editor):
    JobCategory = apps.get_model('jobs', 'JobCategory')
    categories = [
        'Information Technology',
        'Software Development',
        'Data Science',
        'Web Development',
        'Mobile Development',
        'DevOps',
        'Cloud Computing',
        'Cybersecurity',
        'Artificial Intelligence',
        'Machine Learning',
        'Business Analysis',
        'Project Management',
        'Digital Marketing',
        'Sales',
        'Customer Service',
        'Human Resources',
        'Finance',
        'Accounting',
        'Healthcare',
        'Education',
        'Design',
        'Content Writing',
        'Administrative',
        'Engineering',
        'Manufacturing',
        'Legal',
        'Consulting',
        'Research',
        'Operations',
        'Quality Assurance'
    ]
    
    for category_name in categories:
        JobCategory.objects.create(name=category_name)

def remove_job_categories(apps, schema_editor):
    JobCategory = apps.get_model('jobs', 'JobCategory')
    JobCategory.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('jobs', '0002_company_about_company_address_company_careers_and_more'),
    ]

    operations = [
        migrations.RunPython(add_job_categories, remove_job_categories),
    ]
