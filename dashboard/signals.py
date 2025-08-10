from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from leads.models import Lead, LeadActivity
from .models import DashboardPreference, KPITarget

User = get_user_model()

@receiver(post_save, sender=User)
def create_dashboard_preferences(sender, instance, created, **kwargs):
    """Create dashboard preferences for new users"""
    if created:
        DashboardPreference.objects.create(user=instance)

@receiver(post_save, sender=Lead)
def update_lead_kpis(sender, instance, created, **kwargs):
    """Update KPI targets when leads are created or updated"""
    if created and instance.assigned_to:
        # Update leads_created KPI
        current_period_targets = KPITarget.objects.filter(
            user=instance.assigned_to,
            kpi_type='leads_created',
            period_start__lte=instance.created_at.date(),
            period_end__gte=instance.created_at.date(),
            is_active=True
        )
        
        for target in current_period_targets:
            target.current_value += 1
            target.save()
    
    # Update leads_converted KPI if status changed to won
    if not created and instance.status == 'won':
        try:
            old_instance = Lead.objects.get(pk=instance.pk)
            if hasattr(old_instance, 'status') and old_instance.status != 'won' and instance.assigned_to:
                current_period_targets = KPITarget.objects.filter(
                    user=instance.assigned_to,
                    kpi_type='leads_converted',
                    period_start__lte=instance.updated_at.date(),
                    period_end__gte=instance.updated_at.date(),
                    is_active=True
                )
                
                for target in current_period_targets:
                    target.current_value += 1
                    target.save()
        except Lead.DoesNotExist:
            pass

@receiver(post_save, sender=LeadActivity)
def update_activity_kpis(sender, instance, created, **kwargs):
    """Update activity-related KPIs"""
    if created:
        kpi_mapping = {
            'call': 'calls_made',
            'email': 'emails_sent',
            'meeting': 'meetings_scheduled',
        }
        
        kpi_type = kpi_mapping.get(instance.activity_type)
        if kpi_type:
            current_period_targets = KPITarget.objects.filter(
                user=instance.user,
                kpi_type=kpi_type,
                period_start__lte=instance.created_at.date(),
                period_end__gte=instance.created_at.date(),
                is_active=True
            )
            
            for target in current_period_targets:
                target.current_value += 1
                target.save()