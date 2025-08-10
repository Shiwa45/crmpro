from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Lead, LeadSource, LeadActivity
import re

User = get_user_model()

class LeadCreateForm(forms.ModelForm):
    """Form for creating new leads"""
    
    class Meta:
        model = Lead
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'company', 'job_title',
            'source', 'status', 'priority', 'assigned_to', 'address', 'city', 
            'state', 'country', 'postal_code', 'budget', 'requirements', 'notes'
        ]
        widgets = {
            'requirements': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe the lead requirements...'}),
            'notes': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Add any additional notes...'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter full address...'}),
            'budget': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Enter email address'}),
            'phone': forms.TextInput(attrs={'placeholder': '+91 9876543210'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'Enter first name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Enter last name'}),
            'company': forms.TextInput(attrs={'placeholder': 'Enter company name'}),
            'job_title': forms.TextInput(attrs={'placeholder': 'Enter job title'}),
            'city': forms.TextInput(attrs={'placeholder': 'Enter city'}),
            'state': forms.TextInput(attrs={'placeholder': 'Enter state'}),
            'postal_code': forms.TextInput(attrs={'placeholder': 'Enter postal code'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Style all fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # Filter assigned_to based on user role
        if user:
            if user.role == 'sales_rep':
                self.fields['assigned_to'].queryset = User.objects.filter(id=user.id)
                self.fields['assigned_to'].initial = user
                self.fields['assigned_to'].widget = forms.HiddenInput()
            elif user.role == 'sales_manager':
                # Sales managers can assign to their team
                team_members = User.objects.filter(
                    Q(role='sales_rep', department=user.department) | Q(id=user.id),
                    is_active=True
                ).order_by('first_name', 'last_name')
                self.fields['assigned_to'].queryset = team_members
            else:
                self.fields['assigned_to'].queryset = User.objects.filter(
                    role__in=['sales_rep', 'sales_manager'], is_active=True
                ).order_by('first_name', 'last_name')
        
        # Set initial values
        self.fields['country'].initial = 'India'
        self.fields['status'].initial = 'new'
        self.fields['priority'].initial = 'warm'
        
        # Add required field indicators
        required_fields = ['first_name', 'email']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True
    
    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get('email')
        if email:
            # Check if email already exists (excluding current instance if updating)
            existing_lead = Lead.objects.filter(email=email)
            if self.instance and self.instance.pk:
                existing_lead = existing_lead.exclude(pk=self.instance.pk)
            
            if existing_lead.exists():
                raise ValidationError(f'A lead with email "{email}" already exists.')
        
        return email
    
    def clean_phone(self):
        """Validate phone number format"""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove spaces and special characters for validation
            clean_phone = re.sub(r'[^\d+]', '', phone)
            if len(clean_phone) < 10:
                raise ValidationError('Phone number must be at least 10 digits long.')
        
        return phone
    
    def clean_budget(self):
        """Validate budget amount"""
        budget = self.cleaned_data.get('budget')
        if budget and budget < 0:
            raise ValidationError('Budget cannot be negative.')
        
        return budget

class LeadUpdateForm(LeadCreateForm):
    """Form for updating existing leads"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Allow sales reps to update only certain fields
        user = kwargs.get('user')
        if user and user.role == 'sales_rep':
            # Restrict fields that sales reps can modify
            readonly_fields = ['created_by', 'source']
            for field_name in readonly_fields:
                if field_name in self.fields:
                    self.fields[field_name].widget.attrs['readonly'] = True

class LeadActivityForm(forms.ModelForm):
    """Form for adding activities to leads"""
    
    class Meta:
        model = LeadActivity
        fields = ['activity_type', 'subject', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe the activity...'}),
            'subject': forms.TextInput(attrs={'placeholder': 'Enter activity subject...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Style all fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # Make subject and description required
        self.fields['subject'].required = True
        self.fields['description'].required = True
    
    def clean_subject(self):
        """Validate subject length"""
        subject = self.cleaned_data.get('subject')
        if subject and len(subject.strip()) < 3:
            raise ValidationError('Subject must be at least 3 characters long.')
        
        return subject.strip() if subject else subject

class LeadSearchForm(forms.Form):
    """Form for searching and filtering leads"""
    
    search = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by name, email, company...',
            'class': 'form-control'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + Lead.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    priority = forms.ChoiceField(
        choices=[('', 'All Priority')] + Lead.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
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
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter assigned_to choices based on user role
        if user:
            if user.role == 'sales_manager':
                team_members = User.objects.filter(
                    Q(role='sales_rep', department=user.department) | Q(id=user.id),
                    is_active=True
                ).order_by('first_name', 'last_name')
                self.fields['assigned_to'].queryset = team_members
            elif user.role == 'sales_rep':
                # Sales reps can only see their own leads
                self.fields['assigned_to'].widget = forms.HiddenInput()

class BulkUpdateForm(forms.Form):
    """Form for bulk updating leads"""
    
    BULK_ACTIONS = [
        ('change_status', 'Change Status'),
        ('change_priority', 'Change Priority'),
        ('assign_to', 'Assign To'),
    ]
    
    action = forms.ChoiceField(
        choices=BULK_ACTIONS,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    new_status = forms.ChoiceField(
        choices=Lead.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    new_priority = forms.ChoiceField(
        choices=Lead.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    new_assignee = forms.ModelChoiceField(
        queryset=User.objects.filter(role='sales_rep', is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        
        if action == 'change_status' and not cleaned_data.get('new_status'):
            raise ValidationError('Please select a new status.')
        
        if action == 'change_priority' and not cleaned_data.get('new_priority'):
            raise ValidationError('Please select a new priority.')
        
        if action == 'assign_to' and not cleaned_data.get('new_assignee'):
            raise ValidationError('Please select an assignee.')
        
        return cleaned_data