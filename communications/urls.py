# communications/urls.py
from django.urls import path
from . import views

app_name = 'communications'

urlpatterns = [
    # Email Configuration URLs
    path('config/', views.EmailConfigurationListView.as_view(), name='config_list'),
    path('config/create/', views.EmailConfigurationCreateView.as_view(), name='config_create'),
    path('config/<int:pk>/update/', views.EmailConfigurationUpdateView.as_view(), name='config_update'),
    path('config/<int:pk>/test/', views.test_email_config, name='config_test'),
    
    # Email Template URLs
    path('templates/', views.EmailTemplateListView.as_view(), name='template_list'),
    path('templates/create/', views.EmailTemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:pk>/', views.EmailTemplateDetailView.as_view(), name='template_detail'),
    path('templates/<int:pk>/update/', views.EmailTemplateUpdateView.as_view(), name='template_update'),
    path('templates/<int:pk>/preview/', views.template_preview, name='template_preview'),
    
    # Email Campaign URLs
    path('campaigns/', views.EmailCampaignListView.as_view(), name='campaign_list'),
    path('campaigns/create/', views.EmailCampaignCreateView.as_view(), name='campaign_create'),
    path('campaigns/<int:pk>/', views.EmailCampaignDetailView.as_view(), name='campaign_detail'),
    path('campaigns/<int:pk>/start/', views.start_campaign, name='campaign_start'),
    path('campaigns/<int:pk>/pause/', views.pause_campaign, name='campaign_pause'),
    
    # Quick Email URLs
    path('send/<int:lead_id>/', views.send_quick_email, name='send_quick_email'),
    path('bulk-email/', views.bulk_email, name='bulk_email'),
    
    # Email Sequence URLs
    path('sequences/', views.EmailSequenceListView.as_view(), name='sequence_list'),
    path('sequences/create/', views.EmailSequenceCreateView.as_view(), name='sequence_create'),
    path('sequences/<int:pk>/', views.EmailSequenceDetailView.as_view(), name='sequence_detail'),
    path('sequences/<int:sequence_id>/add-step/', views.add_sequence_step, name='sequence_add_step'),
    
    # Email Management URLs
    path('emails/', views.email_list, name='email_list'),
    path('emails/<int:pk>/', views.email_detail, name='email_detail'),
    
    # Analytics URLs
    path('analytics/', views.email_analytics, name='analytics'),
    
    # Tracking URLs
    path('track/<uuid:tracking_id>/<str:event>/', views.email_tracking, name='email_tracking'),
]