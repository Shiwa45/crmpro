# communications/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from leads.models import Lead, LeadSource
from .models import (
    EmailConfiguration, EmailTemplate, EmailCampaign, 
    Email, EmailSequence, EmailSequenceStep
)

User = get_user_model()

class EmailConfigurationForm(forms.ModelForm):
    """Form for email configuration setup"""
    
    class Meta:
        model = EmailConfiguration
        fields = [
            'name', 'provider', 'smtp_host', 'smtp_port', 'smtp_username', 
            'smtp_password', 'use_tls', 'use_ssl', 'from_email', 'from_name', 
            'reply_to', 'is_default', 'daily_limit'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., My Gmail Account'
            }),
            'provider': forms.Select(attrs={'class': 'form-control'}),
            'smtp_host': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'smtp.gmail.com'
            }),
            'smtp_port': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '587'
            }),
            'smtp_username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'your.email@gmail.com'
            }),
            'smtp_password': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your app password'
            }),
            'from_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your.email@company.com'
            }),
            'from_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Name'
            }),
            'reply_to': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional reply-to email'
            }),
            'daily_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '10000'
            }),
            'use_tls': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'use_ssl': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set help texts
        self.fields['smtp_password'].help_text = 'Use app passwords for Gmail/Outlook'
        self.fields['daily_limit'].help_text = 'Maximum emails per day (recommended: 500 for Gmail)'
        self.fields['is_default'].help_text = 'Use this configuration by default'
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance

class EmailTemplateForm(forms.ModelForm):
    """Form for creating/editing email templates"""
    
    class Meta:
        model = EmailTemplate
        fields = [
            'name', 'template_type', 'subject', 'body_html', 'body_text', 
            'is_shared'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Template name'
            }),
            'template_type': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email subject line'
            }),
            'body_html': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 15,
                'placeholder': 'HTML email content...'
            }),
            'body_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Plain text version (optional)'
            }),
            'is_shared': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add help text with available variables
        variables_help = """
        Available variables:
        {{lead_name}} - Lead's full name
        {{first_name}} - Lead's first name
        {{last_name}} - Lead's last name
        {{company}} - Lead's company
        {{email}} - Lead's email
        {{phone}} - Lead's phone
        {{user_name}} - Your name
        {{user_email}} - Your email
        {{current_date}} - Current date
        """
        self.fields['body_html'].help_text = variables_help
        self.fields['is_shared'].help_text = 'Allow team members to use this template'
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        
        # Set variables help text
        instance.variables_help = self.fields['body_html'].help_text
        
        if commit:
            instance.save()
        return instance

class QuickEmailForm(forms.Form):
    """Form for sending quick emails to leads"""
    
    template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.none(),
        required=False,
        empty_label="Choose a template (optional)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    subject = forms.CharField(
        max_length=300,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email subject'
        })
    )
    
    body_html = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'Email content...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        lead = kwargs.pop('lead', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Show user's templates and shared templates
            self.fields['template'].queryset = EmailTemplate.objects.filter(
                models.Q(user=user) | models.Q(is_shared=True),
                is_active=True
            ).order_by('name')
        
        self.user = user
        self.lead = lead
    
    def clean(self):
        cleaned_data = super().clean()
        
        # If template is selected, populate subject and body
        template = cleaned_data.get('template')
        if template and not cleaned_data.get('subject'):
            cleaned_data['subject'] = template.subject
        
        if template and not cleaned_data.get('body_html'):
            cleaned_data['body_html'] = template.body_html
        
        return cleaned_data

class EmailCampaignForm(forms.ModelForm):
    """Form for creating email campaigns"""
    
    class Meta:
        model = EmailCampaign
        fields = [
            'name', 'template', 'scheduled_at', 'send_now',
            'target_all_leads', 'target_statuses', 'target_priorities', 
            'target_sources', 'batch_size', 'delay_between_batches'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Campaign name'
            }),
            'template': forms.Select(attrs={'class': 'form-control'}),
            'scheduled_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'send_now': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'target_all_leads': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'target_statuses': forms.CheckboxSelectMultiple(),
            'target_priorities': forms.CheckboxSelectMultiple(),
            'target_sources': forms.CheckboxSelectMultiple(),
            'batch_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '500'
            }),
            'delay_between_batches': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '30',
                'max': '3600'
            }),
        }
    
    # Dynamic choice fields
    target_statuses = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False
    )
    
    target_priorities = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False
    )
    
    target_sources = forms.ModelMultipleChoiceField(
        queryset=LeadSource.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set dynamic choices
        from leads.models import Lead
        self.fields['target_statuses'].choices = Lead.STATUS_CHOICES
        self.fields['target_priorities'].choices = Lead.PRIORITY_CHOICES
        
        if self.user:
            # Filter templates to user's templates and shared templates
            self.fields['template'].queryset = EmailTemplate.objects.filter(
                models.Q(user=self.user) | models.Q(is_shared=True),
                is_active=True
            )
        
        # Set help texts
        self.fields['batch_size'].help_text = 'Number of emails to send at once'
        self.fields['delay_between_batches'].help_text = 'Delay in seconds between batches'
        self.fields['send_now'].help_text = 'Send immediately or schedule for later'
    
    def clean(self):
        cleaned_data = super().clean()
        send_now = cleaned_data.get('send_now')
        scheduled_at = cleaned_data.get('scheduled_at')
        
        if not send_now and not scheduled_at:
            raise ValidationError('Either select "Send Now" or set a scheduled time.')
        
        if send_now and scheduled_at:
            cleaned_data['scheduled_at'] = None
        
        # Validate targeting
        target_all = cleaned_data.get('target_all_leads')
        has_specific_targets = any([
            cleaned_data.get('target_statuses'),
            cleaned_data.get('target_priorities'),
            cleaned_data.get('target_sources'),
        ])
        
        if not target_all and not has_specific_targets:
            raise ValidationError('Please select targeting criteria or choose "Target All Leads".')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
            
            # Get default email configuration
            try:
                instance.email_config = EmailConfiguration.objects.filter(
                    user=self.user, is_default=True
                ).first()
                if not instance.email_config:
                    instance.email_config = EmailConfiguration.objects.filter(
                        user=self.user, is_active=True
                    ).first()
            except EmailConfiguration.DoesNotExist:
                pass
        
        if commit:
            instance.save()
            # Calculate recipients
            instance.calculate_recipients()
        
        return instance

class EmailSequenceForm(forms.ModelForm):
    """Form for creating email sequences"""
    
    class Meta:
        model = EmailSequence
        fields = [
            'name', 'description', 'trigger_on_lead_creation',
            'trigger_on_status_change', 'trigger_on_priority_change',
            'delay_start_days', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sequence name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe this sequence...'
            }),
            'trigger_on_lead_creation': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'delay_start_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '365'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    # Dynamic fields for triggers
    trigger_on_status_change = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        help_text='Start sequence when lead status changes to these values'
    )
    
    trigger_on_priority_change = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        help_text='Start sequence when lead priority changes to these values'
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set dynamic choices
        from leads.models import Lead
        self.fields['trigger_on_status_change'].choices = Lead.STATUS_CHOICES
        self.fields['trigger_on_priority_change'].choices = Lead.PRIORITY_CHOICES
        
        # Set help texts
        self.fields['delay_start_days'].help_text = 'Days to wait before starting sequence'
        self.fields['trigger_on_lead_creation'].help_text = 'Start sequence for all new leads'
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance

class EmailSequenceStepForm(forms.ModelForm):
    """Form for adding steps to email sequences"""
    
    class Meta:
        model = EmailSequenceStep
        fields = [
            'template', 'step_number', 'delay_days',
            'send_only_if_not_replied', 'send_only_if_status'
        ]
        widgets = {
            'template': forms.Select(attrs={'class': 'form-control'}),
            'step_number': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'delay_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'send_only_if_not_replied': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    send_only_if_status = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        help_text='Only send if lead has these statuses'
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        sequence = kwargs.pop('sequence', None)
        super().__init__(*args, **kwargs)
        
        # Set dynamic choices
        from leads.models import Lead
        self.fields['send_only_if_status'].choices = Lead.STATUS_CHOICES
        
        if user:
            # Filter templates
            self.fields['template'].queryset = EmailTemplate.objects.filter(
                models.Q(user=user) | models.Q(is_shared=True),
                is_active=True
            )
        
        if sequence:
            self.sequence = sequence
            # Auto-set next step number
            last_step = sequence.steps.aggregate(
                max_step=models.Max('step_number')
            )['max_step'] or 0
            self.fields['step_number'].initial = last_step + 1
        
        # Set help texts
        self.fields['delay_days'].help_text = 'Days after previous step'
        self.fields['send_only_if_not_replied'].help_text = 'Skip if lead has replied to previous emails'
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if hasattr(self, 'sequence'):
            instance.sequence = self.sequence
        if commit:
            instance.save()
        return instance

class BulkEmailForm(forms.Form):
    """Form for sending bulk emails to selected leads"""
    
    template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Choose an email template'
    )
    
    email_config = forms.ModelChoiceField(
        queryset=EmailConfiguration.objects.none(),
        required=False,
        empty_label='Use default configuration',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Email configuration to use (optional)'
    )
    
    schedule_send = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Schedule for later sending'
    )
    
    scheduled_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        help_text='When to send the emails'
    )
    
    leads = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['template'].queryset = EmailTemplate.objects.filter(
                models.Q(user=user) | models.Q(is_shared=True),
                is_active=True
            )
            
            self.fields['email_config'].queryset = EmailConfiguration.objects.filter(
                user=user, is_active=True
            )
    
    def clean(self):
        cleaned_data = super().clean()
        schedule_send = cleaned_data.get('schedule_send')
        scheduled_at = cleaned_data.get('scheduled_at')
        
        if schedule_send and not scheduled_at:
            raise ValidationError('Please set a scheduled time.')
        
        # Parse leads from hidden field
        leads_data = cleaned_data.get('leads')
        if leads_data:
            try:
                import json
                lead_ids = json.loads(leads_data)
                cleaned_data['lead_objects'] = Lead.objects.filter(id__in=lead_ids)
            except (json.JSONDecodeError, ValueError):
                raise ValidationError('Invalid leads data.')
        else:
            raise ValidationError('No leads selected.')
        
        return cleaned_data

class EmailTestForm(forms.Form):
    """Form for testing email configuration"""
    
    test_email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email to send test to'
        }),
        help_text='We will send a test email to this address'
    )
    
    def __init__(self, *args, **kwargs):
        self.email_config = kwargs.pop('email_config', None)
        super().__init__(*args, **kwargs)

class EmailStatsFilterForm(forms.Form):
    """Form for filtering email statistics"""
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    campaign = forms.ModelChoiceField(
        queryset=EmailCampaign.objects.none(),
        required=False,
        empty_label='All Campaigns',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    template = forms.ModelChoiceField(
        queryset=EmailTemplate.objects.none(),
        required=False,
        empty_label='All Templates',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Email.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['campaign'].queryset = EmailCampaign.objects.filter(user=user)
            self.fields['template'].queryset = EmailTemplate.objects.filter(
                models.Q(user=user) | models.Q(is_shared=True)
            )