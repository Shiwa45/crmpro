# communications/services.py
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.utils import formataddr
from email import encoders
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.template import Template, Context
from django.core.mail import send_mail, EmailMultiAlternatives
from django.urls import reverse
# from django.contrib.sites.models import Site  # Removed Sites dependency

from .models import (
    EmailConfiguration, EmailTemplate, Email, EmailCampaign,
    EmailTracking, EmailSequence, EmailSequenceEnrollment
)
from leads.models import Lead, LeadActivity

logger = logging.getLogger(__name__)

class EmailService:
    """Service class for handling email operations"""
    
    def __init__(self, email_config: EmailConfiguration):
        self.config = email_config
        
    def test_connection(self) -> Tuple[bool, str]:
        """Test email configuration connection"""
        try:
            if self.config.provider == 'smtp':
                return self._test_smtp_connection()
            else:
                # For other providers, implement specific tests
                return self._test_smtp_connection()
        except Exception as e:
            logger.error(f"Email connection test failed: {str(e)}")
            return False, f"Connection failed: {str(e)}"
    
    def _test_smtp_connection(self) -> Tuple[bool, str]:
        """Test SMTP connection"""
        try:
            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port)
            else:
                server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
                if self.config.use_tls:
                    server.starttls()
            
            server.login(self.config.smtp_username, self.config.smtp_password)
            server.quit()
            
            return True, "Connection successful"
        except smtplib.SMTPAuthenticationError:
            return False, "Authentication failed. Check username and password."
        except smtplib.SMTPConnectError:
            return False, "Could not connect to SMTP server. Check host and port."
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def send_email(self, email: Email) -> Tuple[bool, str]:
        """Send a single email"""
        try:
            # Mark as sending
            email.status = 'sending'
            email.save()
            
            # Create email message
            if email.body_html and email.body_text:
                msg = EmailMultiAlternatives(
                    subject=email.subject,
                    body=email.body_text,
                    from_email=formataddr((email.from_name, email.from_email)),
                    to=[email.to_email],
                    reply_to=[email.reply_to] if email.reply_to else None
                )
                msg.attach_alternative(email.body_html, "text/html")
            else:
                # Plain text or HTML only
                content = email.body_html or email.body_text
                content_type = 'html' if email.body_html else 'plain'
                
                msg = EmailMultiAlternatives(
                    subject=email.subject,
                    body=content,
                    from_email=formataddr((email.from_name, email.from_email)),
                    to=[email.to_email],
                    reply_to=[email.reply_to] if email.reply_to else None
                )
                
                if content_type == 'html':
                    msg.content_subtype = 'html'
            
            # Add tracking pixel for HTML emails
            if email.body_html:
                tracking_url = self._get_tracking_url(email, 'opened')
                tracking_pixel = f'<img src="{tracking_url}" width="1" height="1" style="display:none;" />'
                msg.attach_alternative(email.body_html + tracking_pixel, "text/html")
            
            # Configure SMTP backend
            connection = self._get_smtp_connection()
            
            # Send email
            result = msg.send(using=connection)
            
            if result:
                email.status = 'sent'
                email.sent_at = timezone.now()
                email.save()
                
                # Create tracking event
                EmailTracking.objects.create(
                    email=email,
                    event_type='sent'
                )
                
                # Log activity on lead
                LeadActivity.objects.create(
                    lead=email.lead,
                    user=email.user,
                    activity_type='email',
                    subject=f'Email sent: {email.subject}',
                    description=f'Email sent to {email.to_email}'
                )
                
                return True, "Email sent successfully"
            else:
                email.status = 'failed'
                email.error_message = "Failed to send email"
                email.save()
                return False, "Failed to send email"
                
        except Exception as e:
            logger.error(f"Failed to send email {email.id}: {str(e)}")
            email.status = 'failed'
            email.error_message = str(e)
            email.retry_count += 1
            email.save()
            
            return False, str(e)
    
    def _get_smtp_connection(self):
        """Get SMTP connection for Django"""
        from django.core.mail import get_connection
        
        return get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=self.config.smtp_host,
            port=self.config.smtp_port,
            username=self.config.smtp_username,
            password=self.config.smtp_password,
            use_tls=self.config.use_tls,
            use_ssl=self.config.use_ssl,
        )
    
    def _get_tracking_url(self, email: Email, event_type: str) -> str:
        """Generate tracking URL for email events"""
        # Use Django settings instead of Sites framework
        from django.conf import settings
        domain = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
        url = reverse('communications:email_tracking', kwargs={
            'tracking_id': email.tracking_id,
            'event': event_type
        })
        return f"http://{domain}{url}"
    
    def send_test_email(self, test_email: str) -> Tuple[bool, str]:
        """Send a test email to verify configuration"""
        try:
            subject = f"Test Email from {self.config.name}"
            body = f"""
            This is a test email from your CRM system.
            
            Configuration: {self.config.name}
            Provider: {self.config.get_provider_display()}
            From: {self.config.from_name} <{self.config.from_email}>
            
            If you received this email, your configuration is working correctly!
            
            Sent at: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=formataddr((self.config.from_name, self.config.from_email)),
                to=[test_email]
            )
            
            connection = self._get_smtp_connection()
            result = msg.send(using=connection)
            
            if result:
                return True, f"Test email sent successfully to {test_email}"
            else:
                return False, "Failed to send test email"
                
        except Exception as e:
            logger.error(f"Test email failed: {str(e)}")
            return False, f"Test email failed: {str(e)}"

class EmailTemplateService:
    """Service for email template operations"""
    
    @staticmethod
    def render_template(template: EmailTemplate, lead: Lead, user) -> Dict[str, str]:
        """Render email template with lead and user data"""
        context = {
            'lead_name': lead.get_full_name(),
            'first_name': lead.first_name,
            'last_name': lead.last_name or '',
            'company': lead.company or '',
            'email': lead.email,
            'phone': lead.phone or '',
            'user_name': user.get_full_name(),
            'user_email': user.email,
            'current_date': timezone.now().strftime('%B %d, %Y'),
            'current_time': timezone.now().strftime('%H:%M'),
        }
        
        return template.get_rendered_content(context)
    
    @staticmethod
    def get_default_templates(user) -> List[EmailTemplate]:
        """Get default email templates for a user"""
        templates = []
        
        # Welcome template
        welcome_template = EmailTemplate(
            user=user,
            name="Welcome Email",
            template_type="welcome",
            subject="Welcome {{first_name}}! Let's get started",
            body_html="""
            <p>Hi {{first_name}},</p>
            
            <p>Thank you for your interest in our services! I'm {{user_name}} and I'll be your point of contact.</p>
            
            <p>I'd love to learn more about {{company}} and how we can help you achieve your goals.</p>
            
            <p>Would you be available for a quick 15-minute call this week? I have some availability on:</p>
            <ul>
                <li>Tomorrow at 2:00 PM</li>
                <li>Wednesday at 10:00 AM</li>
                <li>Thursday at 3:00 PM</li>
            </ul>
            
            <p>Looking forward to connecting with you!</p>
            
            <p>Best regards,<br>{{user_name}}<br>{{user_email}}</p>
            """,
            is_active=True
        )
        templates.append(welcome_template)
        
        # Follow-up template
        followup_template = EmailTemplate(
            user=user,
            name="Follow-up Email",
            template_type="follow_up",
            subject="Following up on our conversation",
            body_html="""
            <p>Hi {{first_name}},</p>
            
            <p>I wanted to follow up on our previous conversation about {{company}}'s needs.</p>
            
            <p>Have you had a chance to review the information I sent? I'd be happy to answer any questions you might have.</p>
            
            <p>If you'd like to move forward, we could schedule a more detailed discussion about your requirements.</p>
            
            <p>Please let me know your thoughts!</p>
            
            <p>Best regards,<br>{{user_name}}<br>{{user_email}}</p>
            """,
            is_active=True
        )
        templates.append(followup_template)
        
        return templates

class EmailCampaignService:
    """Service for managing email campaigns"""
    
    @staticmethod
    def create_campaign_emails(campaign: EmailCampaign) -> int:
        """Create individual email records for campaign"""
        leads = campaign.get_target_leads()
        emails_created = 0
        
        for lead in leads:
            # Skip if email already exists for this campaign and lead
            if Email.objects.filter(campaign=campaign, lead=lead).exists():
                continue
            
            # Render template content
            template_service = EmailTemplateService()
            rendered_content = template_service.render_template(
                campaign.template, lead, campaign.user
            )
            
            # Create email record
            email = Email.objects.create(
                user=campaign.user,
                lead=lead,
                campaign=campaign,
                template=campaign.template,
                subject=rendered_content['subject'],
                body_html=rendered_content['html_body'],
                body_text=rendered_content['text_body'],
                from_email=campaign.email_config.from_email,
                from_name=campaign.email_config.from_name,
                to_email=lead.email,
                to_name=lead.get_full_name(),
                reply_to=campaign.email_config.reply_to,
                status='queued'
            )
            
            emails_created += 1
        
        # Update campaign stats
        campaign.emails_sent = 0
        campaign.emails_failed = 0
        campaign.save()
        
        return emails_created
    
    @staticmethod
    def send_campaign_batch(campaign: EmailCampaign, batch_size: int = None) -> Dict[str, int]:
        """Send a batch of emails for a campaign"""
        if not batch_size:
            batch_size = campaign.batch_size
        
        # Get queued emails for this campaign
        queued_emails = Email.objects.filter(
            campaign=campaign,
            status='queued'
        )[:batch_size]
        
        if not queued_emails:
            # Campaign is complete
            campaign.status = 'sent'
            campaign.completed_at = timezone.now()
            campaign.save()
            return {'sent': 0, 'failed': 0}
        
        # Send emails
        sent_count = 0
        failed_count = 0
        email_service = EmailService(campaign.email_config)
        
        for email in queued_emails:
            success, message = email_service.send_email(email)
            if success:
                sent_count += 1
            else:
                failed_count += 1
        
        # Update campaign stats
        campaign.emails_sent += sent_count
        campaign.emails_failed += failed_count
        campaign.save()
        
        return {'sent': sent_count, 'failed': failed_count}

class EmailSequenceService:
    """Service for managing email sequences"""
    
    @staticmethod
    def enroll_lead_in_sequence(lead: Lead, sequence: EmailSequence) -> bool:
        """Enroll a lead in an email sequence"""
        try:
            # Check if already enrolled
            enrollment, created = EmailSequenceEnrollment.objects.get_or_create(
                sequence=sequence,
                lead=lead,
                defaults={'is_active': True}
            )
            
            if created:
                # Schedule first email if sequence starts immediately
                if sequence.delay_start_days == 0:
                    EmailSequenceService._schedule_next_step(enrollment)
                
            return created
        except Exception as e:
            logger.error(f"Failed to enroll lead {lead.id} in sequence {sequence.id}: {str(e)}")
            return False
    
    @staticmethod
    def _schedule_next_step(enrollment: EmailSequenceEnrollment):
        """Schedule the next step in a sequence"""
        from django.utils import timezone
        from datetime import timedelta
        
        next_step = enrollment.sequence.steps.filter(
            step_number=enrollment.current_step + 1,
            is_active=True
        ).first()
        
        if not next_step:
            # Sequence complete
            enrollment.is_active = False
            enrollment.completed_at = timezone.now()
            enrollment.save()
            return
        
        # Check conditions
        if next_step.send_only_if_not_replied and enrollment.has_replied:
            # Skip this step
            enrollment.current_step = next_step.step_number
            enrollment.save()
            EmailSequenceService._schedule_next_step(enrollment)
            return
        
        if next_step.send_only_if_status:
            if enrollment.lead.status not in next_step.send_only_if_status:
                # Skip this step
                enrollment.current_step = next_step.step_number
                enrollment.save()
                EmailSequenceService._schedule_next_step(enrollment)
                return
        
        # Create email for this step
        try:
            # Get user's default email config
            email_config = EmailConfiguration.objects.filter(
                user=enrollment.sequence.user,
                is_default=True
            ).first()
            
            if not email_config:
                email_config = EmailConfiguration.objects.filter(
                    user=enrollment.sequence.user,
                    is_active=True
                ).first()
            
            if not email_config:
                logger.error(f"No email configuration found for user {enrollment.sequence.user.id}")
                return
            
            # Render template
            rendered_content = EmailTemplateService.render_template(
                next_step.template, enrollment.lead, enrollment.sequence.user
            )
            
            # Create email
            email = Email.objects.create(
                user=enrollment.sequence.user,
                lead=enrollment.lead,
                template=next_step.template,
                subject=rendered_content['subject'],
                body_html=rendered_content['html_body'],
                body_text=rendered_content['text_body'],
                from_email=email_config.from_email,
                from_name=email_config.from_name,
                to_email=enrollment.lead.email,
                to_name=enrollment.lead.get_full_name(),
                reply_to=email_config.reply_to,
                status='queued'
            )
            
            # Update enrollment
            enrollment.current_step = next_step.step_number
            enrollment.emails_sent += 1
            enrollment.last_email_sent = timezone.now()
            enrollment.save()
            
            # Send immediately or schedule
            email_service = EmailService(email_config)
            email_service.send_email(email)
            
        except Exception as e:
            logger.error(f"Failed to create sequence email: {str(e)}")
    
    @staticmethod
    def process_sequence_triggers():
        """Process all sequence triggers (called by scheduled task)"""
        active_enrollments = EmailSequenceEnrollment.objects.filter(
            is_active=True
        ).select_related('sequence', 'lead')
        
        for enrollment in active_enrollments:
            # Check if it's time for next step
            last_sent = enrollment.last_email_sent or enrollment.enrolled_at
            next_step = enrollment.sequence.steps.filter(
                step_number=enrollment.current_step + 1
            ).first()
            
            if next_step:
                days_since_last = (timezone.now() - last_sent).days
                if days_since_last >= next_step.delay_days:
                    EmailSequenceService._schedule_next_step(enrollment)

class EmailAnalyticsService:
    """Service for email analytics and reporting"""
    
    @staticmethod
    def get_campaign_stats(campaign: EmailCampaign) -> Dict:
        """Get detailed statistics for a campaign"""
        emails = Email.objects.filter(campaign=campaign)
        
        total_sent = emails.filter(status__in=['sent', 'delivered', 'opened', 'clicked']).count()
        delivered = emails.filter(status__in=['delivered', 'opened', 'clicked']).count()
        opened = emails.filter(status__in=['opened', 'clicked']).count()
        clicked = emails.filter(status='clicked').count()
        bounced = emails.filter(status='bounced').count()
        failed = emails.filter(status='failed').count()
        
        return {
            'total_sent': total_sent,
            'delivered': delivered,
            'opened': opened,
            'clicked': clicked,
            'bounced': bounced,
            'failed': failed,
            'delivery_rate': (delivered / total_sent * 100) if total_sent > 0 else 0,
            'open_rate': (opened / delivered * 100) if delivered > 0 else 0,
            'click_rate': (clicked / delivered * 100) if delivered > 0 else 0,
            'bounce_rate': (bounced / total_sent * 100) if total_sent > 0 else 0,
        }
    
    @staticmethod
    def get_template_performance(template: EmailTemplate) -> Dict:
        """Get performance stats for a template"""
        emails = Email.objects.filter(template=template)
        
        total_sent = emails.filter(status__in=['sent', 'delivered', 'opened', 'clicked']).count()
        opened = emails.filter(status__in=['opened', 'clicked']).count()
        clicked = emails.filter(status='clicked').count()
        
        return {
            'total_sent': total_sent,
            'opened': opened,
            'clicked': clicked,
            'open_rate': (opened / total_sent * 100) if total_sent > 0 else 0,
            'click_rate': (clicked / total_sent * 100) if total_sent > 0 else 0,
            'usage_count': template.usage_count,
        }
    
    @staticmethod
    def get_user_email_stats(user, date_from=None, date_to=None) -> Dict:
        """Get email statistics for a user"""
        emails = Email.objects.filter(user=user)
        
        if date_from:
            emails = emails.filter(created_at__date__gte=date_from)
        if date_to:
            emails = emails.filter(created_at__date__lte=date_to)
        
        total_sent = emails.filter(status__in=['sent', 'delivered', 'opened', 'clicked']).count()
        delivered = emails.filter(status__in=['delivered', 'opened', 'clicked']).count()
        opened = emails.filter(status__in=['opened', 'clicked']).count()
        clicked = emails.filter(status='clicked').count()
        
        return {
            'total_sent': total_sent,
            'delivered': delivered,
            'opened': opened,
            'clicked': clicked,
            'delivery_rate': (delivered / total_sent * 100) if total_sent > 0 else 0,
            'open_rate': (opened / delivered * 100) if delivered > 0 else 0,
            'click_rate': (clicked / delivered * 100) if delivered > 0 else 0,
        }