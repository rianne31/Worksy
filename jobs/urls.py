from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.home, name='home'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/<int:job_id>/', views.job_detail, name='job_detail'),
    path('jobs/<int:job_id>/apply/', views.apply_for_job, name='apply_for_job'),
    path('edit-job/<int:job_id>/', views.edit_job, name='edit_job'),
    path('jobs/<int:job_id>/delete/', views.delete_job, name='delete_job'),
    path('jobs/<int:job_id>/applications/', views.view_job_applications, name='view_job_applications'),
    path('post-job/', views.post_job, name='post_job'),
    path('my-jobs/', views.my_jobs, name='my_jobs'),
    path('application-dashboard/', views.application_dashboard, name='application_dashboard'),
    path('employer-dashboard/', views.employer_dashboard, name='employer_dashboard'),
    path('schedule-interview/', views.schedule_interview, name='schedule_interview'),
    path('update-application-status/', views.update_application_status, name='update_application_status'),
    path('jobs/interview/<int:interview_id>/', views.interview_detail, name='interview_detail'),
]

