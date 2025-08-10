# leads/admin.py
from django.contrib import admin
from .models import Lead, LeadSource, LeadActivity

@admin.register(LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']

class LeadActivityInline(admin.TabularInline):
    model = LeadActivity
    extra = 0
    readonly_fields = ['created_at']

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['get_full_name', 'email', 'company', 'status', 'priority', 'assigned_to', 'created_at']
    list_filter = ['status', 'priority', 'source', 'assigned_to', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'company']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'company', 'job_title')
        }),
        ('Lead Details', {
            'fields': ('source', 'status', 'priority', 'assigned_to', 'created_by')
        }),
        ('Address Information', {
            'fields': ('address', 'city', 'state', 'country', 'postal_code'),
            'classes': ('collapse',)
        }),
        ('Business Information', {
            'fields': ('budget', 'requirements', 'notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [LeadActivityInline]

@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):
    list_display = ['lead', 'activity_type', 'subject', 'user', 'created_at']
    list_filter = ['activity_type', 'created_at', 'user']
    search_fields = ['lead__first_name', 'lead__last_name', 'subject']
    readonly_fields = ['created_at']