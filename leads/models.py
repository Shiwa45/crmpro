# leads/models.py
from django.db import models
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class LeadSource(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class Lead(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('qualified', 'Qualified'),
        ('proposal', 'Proposal Sent'),
        ('negotiation', 'Negotiation'),
        ('won', 'Won'),
        ('lost', 'Lost'),
        ('on_hold', 'On Hold'),
    ]
    
    PRIORITY_CHOICES = [
        ('hot', 'Hot'),
        ('warm', 'Warm'),
        ('cold', 'Cold'),
    ]
    
    # Basic Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True, null=True)
    company = models.CharField(max_length=200, blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    
    # Lead Details
    source = models.ForeignKey(LeadSource, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='warm')
    
    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_leads')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_leads')
    
    # Additional Information
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, default='India')
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    
    # Business Information
    budget = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    requirements = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_contacted = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.get_full_name()} - {self.company}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name or ''}".strip()
    
    def get_absolute_url(self):
        return reverse('leads:detail', kwargs={'pk': self.pk})
    
    @property
    def is_hot(self):
        return self.priority == 'hot'
    
    @property
    def is_overdue(self):
        if not self.last_contacted:
            return (timezone.now() - self.created_at).days > 3
        return (timezone.now() - self.last_contacted).days > 7
    
    class Meta:
        ordering = ['-created_at']

class LeadActivity(models.Model):
    ACTIVITY_TYPES = [
        ('call', 'Call'),
        ('email', 'Email'),
        ('meeting', 'Meeting'),
        ('note', 'Note'),
        ('status_change', 'Status Change'),
        ('assignment', 'Assignment'),
    ]
    
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    subject = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.activity_type.title()} - {self.subject}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Lead Activities'