
# communications/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    EmailConfiguration, EmailTemplate, EmailCampaign, Email,
    EmailSequence, EmailSequenceStep, EmailSequenceEnrollment,
    EmailTracking
)

@admin.register(EmailConfiguration)
class EmailConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'provider', 'from_email', 'is_default', 'is_active']
    list_filter = ['provider', 'is_active', 'is_default']
    search_fields = ['name', 'user__username', 'from_email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'provider', 'is_active', 'is_default')
        }),
        ('SMTP Settings', {
            'fields': ('smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'use_tls', 'use_ssl')
        }),
        ('Sender Information', {
            'fields': ('from_email', 'from_name', 'reply_to')
        }),
        ('Limits', {
            'fields': ('daily_limit',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'template_type', 'usage_count', 'is_shared', 'is_active', 'last_used']
    list_filter = ['template_type', 'is_shared', 'is_active', 'created_at']
    search_fields = ['name', 'subject', 'user__username']
    readonly_fields = ['usage_count', 'last_used', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'template_type', 'is_active', 'is_shared')
        }),
        ('Email Content', {
            'fields': ('subject', 'body_html', 'body_text')
        }),
        ('Usage Statistics', {
            'fields': ('usage_count', 'last_used'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'status', 'total_recipients', 'emails_sent', 'emails_failed', 'created_at']
    list_filter = ['status', 'created_at', 'scheduled_at']
    search_fields = ['name', 'user__username']
    readonly_fields = ['total_recipients', 'emails_sent', 'emails_failed', 'started_at', 'completed_at', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Campaign Information', {
            'fields': ('user', 'name', 'template', 'email_config', 'status')
        }),
        ('Scheduling', {
            'fields': ('scheduled_at', 'send_now')
        }),
        ('Targeting', {
            'fields': ('target_all_leads', 'target_statuses', 'target_priorities', 'target_sources')
        }),
        ('Sending Settings', {
            'fields': ('batch_size', 'delay_between_batches')
        }),
        ('Statistics', {
            'fields': ('total_recipients', 'emails_sent', 'emails_failed', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ['subject_short', 'user', 'lead', 'status', 'sent_at', 'opened_at']
    list_filter = ['status', 'sent_at', 'created_at']
    search_fields = ['subject', 'to_email', 'lead__first_name', 'lead__last_name']
    readonly_fields = ['tracking_id', 'sent_at', 'delivered_at', 'opened_at', 'clicked_at', 'created_at']
    
    def subject_short(self, obj):
        return obj.subject[:50] + '...' if len(obj.subject) > 50 else obj.subject
    subject_short.short_description = 'Subject'

@admin.register(EmailSequence)
class EmailSequenceAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_active', 'total_enrollments', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'user__username']
    
    def total_enrollments(self, obj):
        return obj.emailsequenceenrollment_set.count()
    total_enrollments.short_description = 'Total Enrollments'

class EmailSequenceStepInline(admin.TabularInline):
    model = EmailSequenceStep
    extra = 0
    readonly_fields = ['created_at']

@admin.register(EmailSequenceStep)
class EmailSequenceStepAdmin(admin.ModelAdmin):
    list_display = ['sequence', 'step_number', 'template', 'delay_days', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['sequence__name', 'template__name']

@admin.register(EmailSequenceEnrollment)
class EmailSequenceEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['lead', 'sequence', 'current_step', 'is_active', 'emails_sent', 'enrolled_at']
    list_filter = ['is_active', 'enrolled_at', 'completed_at']
    search_fields = ['lead__first_name', 'lead__last_name', 'sequence__name']

@admin.register(EmailTracking)
class EmailTrackingAdmin(admin.ModelAdmin):
    list_display = ['email', 'event_type', 'timestamp', 'ip_address']
    list_filter = ['event_type', 'timestamp']
    search_fields = ['email__subject', 'email__to_email']
    readonly_fields = ['timestamp']
