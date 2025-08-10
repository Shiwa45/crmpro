from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from leads.models import Lead

User = get_user_model()

class DashboardWidget(models.Model):
    """Model for customizable dashboard widgets"""
    WIDGET_TYPES = [
        ('stats_card', 'Statistics Card'),
        ('chart', 'Chart Widget'),
        ('recent_leads', 'Recent Leads'),
        ('top_performers', 'Top Performers'),
        ('activity_feed', 'Activity Feed'),
        ('calendar', 'Calendar Widget'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_widgets')
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES)
    title = models.CharField(max_length=100)
    position = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    configuration = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['position']
        unique_together = ['user', 'widget_type']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"

class DashboardPreference(models.Model):
    """User dashboard preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dashboard_preferences')
    default_date_range = models.CharField(
        max_length=20,
        choices=[
            ('today', 'Today'),
            ('week', 'This Week'),
            ('month', 'This Month'),
            ('quarter', 'This Quarter'),
            ('year', 'This Year'),
        ],
        default='month'
    )
    show_welcome_message = models.BooleanField(default=True)
    auto_refresh_interval = models.IntegerField(default=300)  # seconds
    theme = models.CharField(
        max_length=10,
        choices=[('light', 'Light'), ('dark', 'Dark')],
        default='light'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Dashboard Preferences"

class KPITarget(models.Model):
    """KPI targets for users/teams"""
    KPI_TYPES = [
        ('leads_created', 'Leads Created'),
        ('leads_converted', 'Leads Converted'),
        ('revenue_generated', 'Revenue Generated'),
        ('calls_made', 'Calls Made'),
        ('emails_sent', 'Emails Sent'),
        ('meetings_scheduled', 'Meetings Scheduled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kpi_targets')
    kpi_type = models.CharField(max_length=20, choices=KPI_TYPES)
    target_value = models.DecimalField(max_digits=12, decimal_places=2)
    current_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    period_start = models.DateField()
    period_end = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'kpi_type', 'period_start', 'period_end']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_kpi_type_display()}: {self.current_value}/{self.target_value}"
    
    @property
    def completion_percentage(self):
        if self.target_value > 0:
            return min(100, (float(self.current_value) / float(self.target_value)) * 100)
        return 0
    
    @property
    def is_achieved(self):
        return self.current_value >= self.target_value

class NotificationPreference(models.Model):
    """User notification preferences"""
    NOTIFICATION_TYPES = [
        ('new_lead', 'New Lead Assigned'),
        ('lead_status_change', 'Lead Status Change'),
        ('overdue_follow_up', 'Overdue Follow-up'),
        ('target_achieved', 'Target Achieved'),
        ('daily_summary', 'Daily Summary'),
        ('weekly_report', 'Weekly Report'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_preferences')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    email_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'notification_type']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_notification_type_display()}"