
# communications/tasks.py
from celery import shared_task
from django.utils import timezone
from .models import EmailCampaign, Email
from .services import EmailCampaignService, EmailSequenceService
import logging

logger = logging.getLogger(__name__)

@shared_task
def process_email_campaigns():
    """Process scheduled email campaigns and sequences"""
    try:
        # Process scheduled campaigns
        scheduled_campaigns = EmailCampaign.objects.filter(
            status='scheduled',
            scheduled_at__lte=timezone.now()
        )
        
        for campaign in scheduled_campaigns:
            campaign.status = 'sending'
            campaign.started_at = timezone.now()
            campaign.save()
            
            # Send first batch
            EmailCampaignService.send_campaign_batch(campaign)
        
        # Continue sending campaigns in progress
        sending_campaigns = EmailCampaign.objects.filter(status='sending')
        
        for campaign in sending_campaigns:
            queued_count = Email.objects.filter(
                campaign=campaign,
                status='queued'
            ).count()
            
            if queued_count > 0:
                EmailCampaignService.send_campaign_batch(campaign)
        
        # Process email sequences
        EmailSequenceService.process_sequence_triggers()
        
        logger.info("Email processing completed successfully")
        
    except Exception as e:
        logger.error(f"Email processing failed: {str(e)}")
        raise

@shared_task
def retry_failed_emails():
    """Retry failed emails that haven't exceeded max retries"""
    try:
        from django.db.models import F
        from .models import EmailConfiguration
        from .services import EmailService
        
        failed_emails = Email.objects.filter(
            status='failed',
            retry_count__lt=F('max_retries')
        ).select_related('user')
        
        retried_count = 0
        
        for email in failed_emails:
            email_config = EmailConfiguration.objects.filter(
                user=email.user,
                is_default=True,
                is_active=True
            ).first()
            
            if not email_config:
                email_config = EmailConfiguration.objects.filter(
                    user=email.user,
                    is_active=True
                ).first()
            
            if email_config:
                email_service = EmailService(email_config)
                success, message = email_service.send_email(email)
                
                if success:
                    retried_count += 1
        
        logger.info(f"Retried {retried_count} failed emails")
        
    except Exception as e:
        logger.error(f"Failed email retry failed: {str(e)}")
        raise
