# Generated by Django 4.2.21 on 2025-05-12 14:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0004_alter_interview_options_alter_interview_created_at'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='interview',
            options={},
        ),
        migrations.AlterField(
            model_name='interview',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
