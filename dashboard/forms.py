from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from leads.models import LeadSource
from .models import DashboardPreference, KPITarget, NotificationPreference

User = get_user_model()

class DashboardFilterForm(forms.Form):
    """Form for filtering dashboard data"""
    
    DATE_RANGE_CHOICES = [
        ('today', 'Today'),
        ('week', 'This Week'),
        ('month', 'This Month'),
        ('quarter', 'This Quarter'),
        ('year', 'This Year'),
        ('custom', 'Custom Range'),
    ]
    
    date_range = forms.ChoiceField(
        choices=DATE_RANGE_CHOICES,
        initial='month',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'style': 'display: none;'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'style': 'display: none;'
        })
    )
    
    source = forms.ModelChoiceField(
        queryset=LeadSource.objects.filter(is_active=True),
        required=False,
        empty_label="All Sources",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(role='sales_rep', is_active=True),
        required=False,
        empty_label="All Assignees",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter assigned_to choices based on user role
        if user:
            if user.role == 'sales_manager':
                team_members = User.objects.filter(
                    role='sales_rep', 
                    department=user.department, 
                    is_active=True
                ).order_by('first_name', 'last_name')
                self.fields['assigned_to'].queryset = team_members
            elif user.role == 'sales_rep':
                # Sales reps only see their own data
                self.fields['assigned_to'].widget = forms.HiddenInput()
                self.fields['assigned_to'].initial = user
    
    def clean(self):
        cleaned_data = super().clean()
        date_range = cleaned_data.get('date_range')
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_range == 'custom':
            if not date_from or not date_to:
                raise ValidationError('Both start and end dates are required for custom range.')
            if date_from > date_to:
                raise ValidationError('Start date must be before end date.')
        
        return cleaned_data

class ReportGeneratorForm(forms.Form):
    """Form for generating custom reports"""
    
    REPORT_TYPES = [
        ('summary', 'Executive Summary'),
        ('detailed_leads', 'Detailed Leads Report'),
        ('conversion_analysis', 'Conversion Analysis'),
        ('source_performance', 'Source Performance Report'),
        ('team_performance', 'Team Performance Report'),
        ('activity_report', 'Activity Report'),
        ('revenue_analysis', 'Revenue Analysis'),
    ]
    
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
    ]
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    date_to = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        initial='csv',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    include_charts = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default date range (last month)
        today = date.today()
        last_month = today.replace(day=1) - timedelta(days=1)
        last_month_start = last_month.replace(day=1)
        
        self.fields['date_from'].initial = last_month_start
        self.fields['date_to'].initial = last_month
        
        # Hide team performance for sales reps
        if user and user.role == 'sales_rep':
            choices = [choice for choice in self.REPORT_TYPES if choice[0] != 'team_performance']
            self.fields['report_type'].choices = choices
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError('Start date must be before end date.')
        
        return cleaned_data

class DashboardPreferenceForm(forms.ModelForm):
    """Form for dashboard preferences"""
    
    class Meta:
        model = DashboardPreference
        fields = [
            'default_date_range', 
            'show_welcome_message', 
            'auto_refresh_interval', 
            'theme'
        ]
        widgets = {
            'default_date_range': forms.Select(attrs={'class': 'form-control'}),
            'show_welcome_message': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'auto_refresh_interval': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '60',
                'max': '3600',
                'step': '60'
            }),
            'theme': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['auto_refresh_interval'].help_text = 'Auto-refresh interval in seconds (60-3600)'
        self.fields['show_welcome_message'].help_text = 'Show welcome message on dashboard'
        self.fields['theme'].help_text = 'Choose your preferred theme'

class KPITargetForm(forms.ModelForm):
    """Form for KPI targets"""
    
    class Meta:
        model = KPITarget
        fields = ['kpi_type', 'target_value', 'period_start', 'period_end']
        widgets = {
            'kpi_type': forms.Select(attrs={'class': 'form-control'}),
            'target_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'period_start': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control'
            }),
            'period_end': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default period (current month)
        today = date.today()
        month_start = today.replace(day=1)
        next_month = month_start.replace(month=month_start.month + 1) if month_start.month < 12 else month_start.replace(year=month_start.year + 1, month=1)
        month_end = next_month - timedelta(days=1)
        
        self.fields['period_start'].initial = month_start
        self.fields['period_end'].initial = month_end
    
    def clean(self):
        cleaned_data = super().clean()
        period_start = cleaned_data.get('period_start')
        period_end = cleaned_data.get('period_end')
        target_value = cleaned_data.get('target_value')
        
        if period_start and period_end and period_start >= period_end:
            raise ValidationError('Period start must be before period end.')
        
        if target_value and target_value <= 0:
            raise ValidationError('Target value must be greater than 0.')
        
        return cleaned_data

class NotificationPreferenceForm(forms.ModelForm):
    """Form for notification preferences"""
    
    class Meta:
        model = NotificationPreference
        fields = ['notification_type', 'email_enabled', 'in_app_enabled', 'sms_enabled']
        widgets = {
            'notification_type': forms.Select(attrs={'class': 'form-control'}),
            'email_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'in_app_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }