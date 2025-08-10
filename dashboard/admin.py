from django.contrib import admin
from django.utils.html import format_html
from .models import DashboardWidget, DashboardPreference, KPITarget, NotificationPreference

@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ['user', 'widget_type', 'title', 'position', 'is_visible', 'created_at']
    list_filter = ['widget_type', 'is_visible', 'created_at']
    search_fields = ['user__username', 'user__email', 'title']
    ordering = ['user', 'position']
    list_editable = ['position', 'is_visible']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'widget_type', 'title', 'position', 'is_visible')
        }),
        ('Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

@admin.register(DashboardPreference)
class DashboardPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'default_date_range', 'theme', 'show_welcome_message', 'auto_refresh_interval']
    list_filter = ['default_date_range', 'theme', 'show_welcome_message']
    search_fields = ['user__username', 'user__email']
    ordering = ['user']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Display Preferences', {
            'fields': ('default_date_range', 'theme', 'show_welcome_message')
        }),
        ('Behavior', {
            'fields': ('auto_refresh_interval',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']

@admin.register(KPITarget)
class KPITargetAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'kpi_type', 'target_value', 'current_value', 
        'completion_percentage_display', 'period_display', 'is_active'
    ]
    list_filter = ['kpi_type', 'is_active', 'period_start', 'period_end']
    search_fields = ['user__username', 'user__email']
    ordering = ['-period_start', 'user']
    list_editable = ['is_active']
    
    fieldsets = (
        ('Target Information', {
            'fields': ('user', 'kpi_type', 'target_value', 'current_value')
        }),
        ('Period', {
            'fields': ('period_start', 'period_end', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def completion_percentage_display(self, obj):
        percentage = obj.completion_percentage
        color = 'green' if percentage >= 100 else 'orange' if percentage >= 75 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color,
            percentage
        )
    completion_percentage_display.short_description = 'Completion %'
    
    def period_display(self, obj):
        return f"{obj.period_start} to {obj.period_end}"
    period_display.short_description = 'Period'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'notification_type', 'email_enabled', 
        'in_app_enabled', 'sms_enabled'
    ]
    list_filter = [
        'notification_type', 'email_enabled', 
        'in_app_enabled', 'sms_enabled'
    ]
    search_fields = ['user__username', 'user__email']
    ordering = ['user', 'notification_type']
    list_editable = ['email_enabled', 'in_app_enabled', 'sms_enabled']
    
    fieldsets = (
        ('User & Type', {
            'fields': ('user', 'notification_type')
        }),
        ('Notification Channels', {
            'fields': ('email_enabled', 'in_app_enabled', 'sms_enabled')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')