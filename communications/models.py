# communications/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from leads.models import Lead
import uuid

User = get_user_model()

class EmailConfiguration(models.Model):
    """Email configuration for different providers"""
    PROVIDER_CHOICES = [
        ('smtp', 'Custom SMTP'),
        ('gmail', 'Gmail'),
        ('outlook', 'Outlook'),
        ('sendgrid', 'SendGrid'),
        ('ses', 'Amazon SES'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_configs')
    name = models.CharField(max_length=100, help_text="Configuration name")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    
    # SMTP Settings
    smtp_host = models.CharField(max_length=255, blank=True)
    smtp_port = models.IntegerField(default=587)
    smtp_username = models.CharField(max_length=255, blank=True)
    smtp_password = models.CharField(max_length=255, blank=True)
    use_tls = models.BooleanField(default=True)
    use_ssl = models.BooleanField(default=False)
    
    # Sender Information
    from_email = models.EmailField()
    from_name = models.CharField(max_length=100)
    reply_to = models.EmailField(blank=True)
    
    # Settings
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    daily_limit = models.IntegerField(default=500, help_text="Daily email limit")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'name']
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.provider})"
    
    def save(self, *args, **kwargs):
        # Ensure only one default config per user
        if self.is_default:
            EmailConfiguration.objects.filter(
                user=self.user, is_default=True
            ).update(is_default=False)
        super().save(*args, **kwargs)

class EmailTemplate(models.Model):
    """Email templates for different scenarios"""
    TEMPLATE_TYPES = [
        ('welcome', 'Welcome Email'),
        ('follow_up', 'Follow-up Email'),
        ('quote_request', 'Quote Request'),
        ('proposal', 'Proposal Email'),
        ('thank_you', 'Thank You Email'),
        ('nurture', 'Nurture Campaign'),
        ('appointment', 'Appointment Confirmation'),
        ('custom', 'Custom Template'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_templates')
    name = models.CharField(max_length=200)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    subject = models.CharField(max_length=300)
    body_html = models.TextField(help_text="HTML content of the email")
    body_text = models.TextField(blank=True, help_text="Plain text version")
    
    # Template Variables
    variables_help = models.TextField(
        blank=True,
        help_text="Available variables: {{lead_name}}, {{company}}, {{user_name}}, etc."
    )
    
    # Settings
    is_active = models.BooleanField(default=True)
    is_shared = models.BooleanField(default=False, help_text="Share with team")
    
    # Usage Stats
    usage_count = models.IntegerField(default=0)
    last_used = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-last_used', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
    
    def get_rendered_content(self, context):
        """Render template with context variables"""
        from django.template import Template, Context
        
        # Render subject
        subject_template = Template(self.subject)
        rendered_subject = subject_template.render(Context(context))
        
        # Render HTML body
        html_template = Template(self.body_html)
        rendered_html = html_template.render(Context(context))
        
        # Render text body
        if self.body_text:
            text_template = Template(self.body_text)
            rendered_text = text_template.render(Context(context))
        else:
            # Basic HTML to text conversion
            from django.utils.html import strip_tags
            rendered_text = strip_tags(rendered_html)
        
        return {
            'subject': rendered_subject,
            'html_body': rendered_html,
            'text_body': rendered_text
        }

class EmailCampaign(models.Model):
    """Email campaigns for bulk sending"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ]
    
    name = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_campaigns')
    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE)
    email_config = models.ForeignKey(EmailConfiguration, on_delete=models.CASCADE)
    
    # Campaign Settings
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_at = models.DateTimeField(blank=True, null=True)
    send_now = models.BooleanField(default=False)
    
    # Targeting
    target_all_leads = models.BooleanField(default=False)
    target_statuses = models.JSONField(default=list, blank=True)
    target_priorities = models.JSONField(default=list, blank=True)
    target_sources = models.JSONField(default=list, blank=True)
    specific_leads = models.ManyToManyField(Lead, blank=True)
    
    # Sending Settings
    batch_size = models.IntegerField(default=50, help_text="Emails per batch")
    delay_between_batches = models.IntegerField(default=60, help_text="Seconds between batches")
    
    # Statistics
    total_recipients = models.IntegerField(default=0)
    emails_sent = models.IntegerField(default=0)
    emails_failed = models.IntegerField(default=0)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.status})"
    
    def get_target_leads(self):
        """Get leads that match campaign targeting criteria"""
        if self.target_all_leads:
            queryset = Lead.objects.all()
        else:
            queryset = Lead.objects.none()
            
            # Filter by status
            if self.target_statuses:
                queryset = queryset.union(Lead.objects.filter(status__in=self.target_statuses))
            
            # Filter by priority
            if self.target_priorities:
                queryset = queryset.union(Lead.objects.filter(priority__in=self.target_priorities))
            
            # Filter by source
            if self.target_sources:
                queryset = queryset.union(Lead.objects.filter(source_id__in=self.target_sources))
            
            # Add specific leads
            if self.specific_leads.exists():
                queryset = queryset.union(self.specific_leads.all())
        
        # Exclude leads without email
        return queryset.filter(email__isnull=False).exclude(email='').distinct()
    
    def calculate_recipients(self):
        """Calculate and update total recipients"""
        self.total_recipients = self.get_target_leads().count()
        self.save()
        return self.total_recipients

class Email(models.Model):
    """Individual email records"""
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('replied', 'Replied'),
        ('bounced', 'Bounced'),
        ('failed', 'Failed'),
        ('spam', 'Marked as Spam'),
    ]
    
    # Unique identifier for tracking
    tracking_id = models.UUIDField(default=uuid.uuid4, unique=True)
    
    # Relationships
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_emails')
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='emails')
    campaign = models.ForeignKey(EmailCampaign, on_delete=models.CASCADE, blank=True, null=True)
    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE, blank=True, null=True)
    
    # Email Content
    subject = models.CharField(max_length=300)
    body_html = models.TextField()
    body_text = models.TextField(blank=True)
    
    # Recipients
    from_email = models.EmailField()
    from_name = models.CharField(max_length=100)
    to_email = models.EmailField()
    to_name = models.CharField(max_length=100, blank=True)
    reply_to = models.EmailField(blank=True)
    
    # Status and Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    external_id = models.CharField(max_length=255, blank=True, help_text="Provider's message ID")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    opened_at = models.DateTimeField(blank=True, null=True)
    clicked_at = models.DateTimeField(blank=True, null=True)
    
    # Analytics
    open_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    
    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tracking_id']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['lead', 'created_at']),
        ]
    
    def __str__(self):
        return f"Email to {self.to_email} - {self.subject[:50]}"
    
    def mark_as_opened(self):
        """Mark email as opened"""
        if self.status in ['sent', 'delivered']:
            self.status = 'opened'
            self.opened_at = timezone.now()
            self.open_count += 1
            self.save()
    
    def mark_as_clicked(self):
        """Mark email as clicked"""
        if self.status in ['sent', 'delivered', 'opened']:
            self.status = 'clicked'
            self.clicked_at = timezone.now()
            self.click_count += 1
            if not self.opened_at:
                self.opened_at = timezone.now()
                self.open_count += 1
            self.save()

class EmailTracking(models.Model):
    """Detailed email tracking events"""
    EVENT_TYPES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('bounced', 'Bounced'),
        ('spam', 'Marked as Spam'),
        ('unsubscribed', 'Unsubscribed'),
    ]
    
    email = models.ForeignKey(Email, on_delete=models.CASCADE, related_name='tracking_events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Additional event data
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    clicked_url = models.URLField(blank=True)
    bounce_reason = models.TextField(blank=True)
    
    # Provider data
    provider_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['email', 'event_type']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.email.subject[:30]}"

class EmailSequence(models.Model):
    """Automated email sequences/drip campaigns"""
    name = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_sequences')
    description = models.TextField(blank=True)
    
    # Trigger Settings
    trigger_on_lead_creation = models.BooleanField(default=False)
    trigger_on_status_change = models.JSONField(default=list, blank=True)
    trigger_on_priority_change = models.JSONField(default=list, blank=True)
    
    # Settings
    is_active = models.BooleanField(default=True)
    delay_start_days = models.IntegerField(default=0, help_text="Days to wait before starting")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class EmailSequenceStep(models.Model):
    """Individual steps in an email sequence"""
    sequence = models.ForeignKey(EmailSequence, on_delete=models.CASCADE, related_name='steps')
    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE)
    
    step_number = models.IntegerField()
    delay_days = models.IntegerField(help_text="Days after previous step (or sequence start)")
    
    # Conditions
    send_only_if_not_replied = models.BooleanField(default=True)
    send_only_if_status = models.JSONField(default=list, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['step_number']
        unique_together = ['sequence', 'step_number']
    
    def __str__(self):
        return f"{self.sequence.name} - Step {self.step_number}"

class EmailSequenceEnrollment(models.Model):
    """Track leads enrolled in email sequences"""
    sequence = models.ForeignKey(EmailSequence, on_delete=models.CASCADE)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE)
    
    enrolled_at = models.DateTimeField(auto_now_add=True)
    current_step = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    # Tracking
    emails_sent = models.IntegerField(default=0)
    last_email_sent = models.DateTimeField(blank=True, null=True)
    has_replied = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['sequence', 'lead']
        ordering = ['-enrolled_at']
    
    def __str__(self):
        return f"{self.lead.get_full_name()} in {self.sequence.name}"