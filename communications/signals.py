# communications/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from leads.models import Lead
from .models import EmailSequence, EmailSequenceEnrollment
from .services import EmailSequenceService, EmailTemplateService

User = get_user_model()

@receiver(post_save, sender=User)
def create_default_email_templates(sender, instance, created, **kwargs):
    """Create default email templates for new users"""
    if created:
        # Create default templates
        default_templates = EmailTemplateService.get_default_templates(instance)
        for template in default_templates:
            template.save()

@receiver(post_save, sender=Lead)
def trigger_email_sequences(sender, instance, created, **kwargs):
    """Trigger email sequences based on lead events"""
    if created:
        # Trigger sequences for new leads
        sequences = EmailSequence.objects.filter(
            trigger_on_lead_creation=True,
            is_active=True
        )
        
        for sequence in sequences:
            EmailSequenceService.enroll_lead_in_sequence(instance, sequence)
    
    else:
        # Check for status/priority changes
        if hasattr(instance, '_state') and instance._state.adding is False:
            try:
                old_instance = Lead.objects.get(pk=instance.pk)
                
                # Status change triggers
                if old_instance.status != instance.status:
                    sequences = EmailSequence.objects.filter(
                        trigger_on_status_change__contains=[instance.status],
                        is_active=True
                    )
                    
                    for sequence in sequences:
                        EmailSequenceService.enroll_lead_in_sequence(instance, sequence)
                
                # Priority change triggers
                if old_instance.priority != instance.priority:
                    sequences = EmailSequence.objects.filter(
                        trigger_on_priority_change__contains=[instance.priority],
                        is_active=True
                    )
                    
                    for sequence in sequences:
                        EmailSequenceService.enroll_lead_in_sequence(instance, sequence)
                        
            except Lead.DoesNotExist:
                pass
