from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    """Form for creating new users"""
    email = forms.EmailField(required=True, help_text='Required. Enter a valid email address.')
    first_name = forms.CharField(max_length=30, required=True, help_text='Required.')
    last_name = forms.CharField(max_length=30, required=True, help_text='Required.')
    phone = forms.CharField(max_length=15, required=False, help_text='Optional. Include country code.')
    role = forms.ChoiceField(choices=User.ROLE_CHOICES, required=True)
    department = forms.CharField(max_length=100, required=False, help_text='Optional.')
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 
                 'role', 'department', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            
        # Add placeholders
        self.fields['username'].widget.attrs['placeholder'] = 'Enter username'
        self.fields['email'].widget.attrs['placeholder'] = 'Enter email address'
        self.fields['first_name'].widget.attrs['placeholder'] = 'Enter first name'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Enter last name'
        self.fields['phone'].widget.attrs['placeholder'] = '+91 9876543210'
        self.fields['department'].widget.attrs['placeholder'] = 'e.g., Sales, Marketing'
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone = self.cleaned_data.get('phone', '')
        user.role = self.cleaned_data['role']
        user.department = self.cleaned_data.get('department', '')
        
        if commit:
            user.save()
            # Create user profile
            UserProfile.objects.get_or_create(user=user)
        
        return user

class UserUpdateForm(forms.ModelForm):
    """Form for updating user information"""
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 
                 'department', 'profile_picture']
        
        widgets = {
            'profile_picture': forms.FileInput(attrs={'accept': 'image/*'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes
        for field_name, field in self.fields.items():
            if field_name != 'profile_picture':
                field.widget.attrs['class'] = 'form-control'
            else:
                field.widget.attrs['class'] = 'form-control'
        
        # Add placeholders
        self.fields['first_name'].widget.attrs['placeholder'] = 'Enter first name'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Enter last name'
        self.fields['email'].widget.attrs['placeholder'] = 'Enter email address'
        self.fields['phone'].widget.attrs['placeholder'] = '+91 9876543210'
        self.fields['department'].widget.attrs['placeholder'] = 'e.g., Sales, Marketing'

class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile"""
    
    class Meta:
        model = UserProfile
        fields = ['bio', 'address', 'city', 'state', 'country', 
                 'postal_code', 'date_of_birth']
        
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'bio': forms.Textarea(attrs={'rows': 4}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # Add placeholders
        self.fields['bio'].widget.attrs['placeholder'] = 'Tell us about yourself...'
        self.fields['address'].widget.attrs['placeholder'] = 'Enter your address'
        self.fields['city'].widget.attrs['placeholder'] = 'Enter city'
        self.fields['state'].widget.attrs['placeholder'] = 'Enter state'
        self.fields['country'].widget.attrs['placeholder'] = 'Enter country'
        self.fields['postal_code'].widget.attrs['placeholder'] = 'Enter postal code'

class LoginForm(forms.Form):
    """Custom login form"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )