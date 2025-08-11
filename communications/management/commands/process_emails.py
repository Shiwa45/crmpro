# communications/management/commands/process_emails.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
import logging

from communications.models import EmailCampaign, Email, EmailSequence
from communications.services import EmailCampaignService, EmailSequenceService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process scheduled email campaigns and sequences'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--campaigns',
            action='store_true',
            help='Process scheduled campaigns only',
        )
        parser.add_argument(
            '--sequences',
            action='store_true',
            help='Process email sequences only',
        )
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            help='Retry failed emails',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('Starting email processing...')
        
        if options['campaigns'] or not (options['sequences'] or options['retry_failed']):
            self.process_campaigns()
        
        if options['sequences'] or not (options['campaigns'] or options['retry_failed']):
            self.process_sequences()
        
        if options['retry_failed'] or not (options['campaigns'] or options['sequences']):
            self.retry_failed_emails()
        
        self.stdout.write(
            self.style.SUCCESS('Email processing completed successfully!')
        )
    
    def process_campaigns(self):
        """Process scheduled email campaigns"""
        self.stdout.write('Processing scheduled campaigns...')
        
        # Get campaigns that should be started
        scheduled_campaigns = EmailCampaign.objects.filter(
            status='scheduled',
            scheduled_at__lte=timezone.now()
        )
        
        for campaign in scheduled_campaigns:
            try:
                self.stdout.write(f'Starting campaign: {campaign.name}')
                
                campaign.status = 'sending'
                campaign.started_at = timezone.now()
                campaign.save()
                
                # Send first batch
                result = EmailCampaignService.send_campaign_batch(campaign)
                
                self.stdout.write(
                    f'Campaign {campaign.name}: '
                    f'Sent: {result["sent"]}, Failed: {result["failed"]}'
                )
                
            except Exception as e:
                logger.error(f'Failed to start campaign {campaign.id}: {str(e)}')
                self.stdout.write(
                    self.style.ERROR(f'Failed to start campaign {campaign.name}: {str(e)}')
                )
        
        # Continue sending campaigns that are in progress
        sending_campaigns = EmailCampaign.objects.filter(status='sending')
        
        for campaign in sending_campaigns:
            try:
                # Check if there are queued emails
                queued_count = Email.objects.filter(
                    campaign=campaign,
                    status='queued'
                ).count()
                
                if queued_count > 0:
                    # Send next batch
                    result = EmailCampaignService.send_campaign_batch(campaign)
                    
                    if result['sent'] > 0 or result['failed'] > 0:
                        self.stdout.write(
                            f'Campaign {campaign.name} batch: '
                            f'Sent: {result["sent"]}, Failed: {result["failed"]}'
                        )
                
            except Exception as e:
                logger.error(f'Failed to process campaign {campaign.id}: {str(e)}')
                self.stdout.write(
                    self.style.ERROR(f'Failed to process campaign {campaign.name}: {str(e)}')
                )
    
    def process_sequences(self):
        """Process email sequences"""
        self.stdout.write('Processing email sequences...')
        
        try:
            EmailSequenceService.process_sequence_triggers()
            self.stdout.write('Email sequences processed successfully')
        except Exception as e:
            logger.error(f'Failed to process email sequences: {str(e)}')
            self.stdout.write(
                self.style.ERROR(f'Failed to process email sequences: {str(e)}')
            )
    
    def retry_failed_emails(self):
        """Retry failed emails that haven't exceeded max retries"""
        self.stdout.write('Retrying failed emails...')
        
        # Get failed emails that can be retried
        failed_emails = Email.objects.filter(
            status='failed',
            retry_count__lt=models.F('max_retries')
        ).select_related('user')
        
        retried_count = 0
        
        for email in failed_emails:
            try:
                # Get user's email configuration
                from communications.models import EmailConfiguration
                from communications.services import EmailService
                
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
                        self.stdout.write(f'Retried email {email.id} successfully')
                    else:
                        self.stdout.write(f'Retry failed for email {email.id}: {message}')
                else:
                    self.stdout.write(f'No email config found for user {email.user.id}')
                    
            except Exception as e:
                logger.error(f'Failed to retry email {email.id}: {str(e)}')
                self.stdout.write(
                    self.style.ERROR(f'Failed to retry email {email.id}: {str(e)}')
                )
        
        self.stdout.write(f'Retried {retried_count} failed emails')