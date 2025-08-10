from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser, UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile Information'
    fields = ('bio', 'address', 'city', 'state', 'country', 'postal_code', 'date_of_birth')

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'get_full_name_display', 'role', 
                    'department', 'is_active', 'date_joined']
    list_filter = ['role', 'department', 'is_active', 'date_joined', 'last_login']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    ordering = ['-date_joined']
    list_per_page = 25
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Information', {
            'fields': ('phone', 'role', 'department', 'profile_picture'),
            'classes': ('wide',)
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Personal Information', {
            'fields': ('email', 'first_name', 'last_name', 'phone'),
            'classes': ('wide',)
        }),
        ('Role & Department', {
            'fields': ('role', 'department'),
            'classes': ('wide',)
        }),
    )
    
    inlines = [UserProfileInline]
    
    def get_full_name_display(self, obj):
        return obj.get_full_name() or obj.username
    get_full_name_display.short_description = 'Full Name'
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of superusers
        if obj and obj.is_superuser:
            return False
        return super().has_delete_permission(request, obj)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'city', 'state', 'country', 'date_of_birth']
    list_filter = ['country', 'state', 'city']
    search_fields = ['user__username', 'user__email', 'city', 'state']
    ordering = ['user__username']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')