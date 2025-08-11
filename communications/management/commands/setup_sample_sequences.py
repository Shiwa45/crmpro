# communications/management/commands/setup_sample_sequences.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from communications.models import EmailTemplate, EmailSequence, EmailSequenceStep
from leads.models import Lead

User = get_user_model()

class Command(BaseCommand):
    help = 'Setup sample email sequences and templates for testing'
    
    def handle(self, *args, **options):
        # Get or create a test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write('Created test user: testuser / testpass123')
        
        # Create sample email templates
        templates = [
            {
                'name': 'Welcome Email',
                'template_type': 'welcome',
                'subject': 'Welcome to Our Company!',
                'body_html': '''
                <h2>Welcome {{lead_name}}!</h2>
                <p>Thank you for your interest in our services. We're excited to have you on board!</p>
                <p>Here's what you can expect from us:</p>
                <ul>
                    <li>Quality service</li>
                    <li>Expert support</li>
                    <li>Competitive pricing</li>
                </ul>
                <p>Best regards,<br>The Team</p>
                ''',
                'body_text': 'Welcome! Thank you for your interest in our services.'
            },
            {
                'name': 'Follow-up Email',
                'template_type': 'follow_up',
                'subject': 'Following up on your inquiry',
                'body_html': '''
                <h2>Hi {{lead_name}},</h2>
                <p>I wanted to follow up on your recent inquiry about our services.</p>
                <p>Have you had a chance to review the information we sent? I'd be happy to answer any questions you might have.</p>
                <p>Looking forward to hearing from you!</p>
                <p>Best regards,<br>{{user_name}}</p>
                ''',
                'body_text': 'Following up on your inquiry. Have any questions?'
            },
            {
                'name': 'Case Study Email',
                'template_type': 'nurture',
                'subject': 'Success Story: How We Helped [Company]',
                'body_html': '''
                <h2>Success Story</h2>
                <p>Hi {{lead_name}},</p>
                <p>I wanted to share a recent success story that might be relevant to your situation.</p>
                <p>We recently helped [Company] achieve [specific results] through our services.</p>
                <p>Would you like to learn more about how we could help your business?</p>
                <p>Best regards,<br>{{user_name}}</p>
                ''',
                'body_text': 'Success story: How we helped another company achieve results.'
            },
            {
                'name': 'Special Offer',
                'template_type': 'nurture',
                'subject': 'Exclusive Offer Just for You',
                'body_html': '''
                <h2>Special Offer</h2>
                <p>Hi {{lead_name}},</p>
                <p>As a valued prospect, we'd like to offer you an exclusive deal on our services.</p>
                <p>For a limited time, you can get [specific offer] at [discount].</p>
                <p>This offer expires on [date]. Don't miss out!</p>
                <p>Best regards,<br>{{user_name}}</p>
                ''',
                'body_text': 'Special offer just for you. Limited time only!'
            }
        ]
        
        created_templates = []
        for template_data in templates:
            template, created = EmailTemplate.objects.get_or_create(
                user=user,
                name=template_data['name'],
                defaults=template_data
            )
            created_templates.append(template)
            if created:
                self.stdout.write(f'Created template: {template.name}')
        
        # Create sample email sequences
        sequences = [
            {
                'name': 'Welcome Series',
                'description': 'Automated welcome sequence for new leads',
                'trigger_on_lead_creation': True,
                'delay_start_days': 0,
                'is_active': True
            },
            {
                'name': 'Follow-up Series',
                'description': 'Follow-up sequence for interested prospects',
                'trigger_on_lead_creation': False,
                'delay_start_days': 1,
                'is_active': True
            },
            {
                'name': 'Re-engagement',
                'description': 'Re-engage inactive leads',
                'trigger_on_lead_creation': False,
                'delay_start_days': 30,
                'is_active': False
            }
        ]
        
        created_sequences = []
        for sequence_data in sequences:
            sequence, created = EmailSequence.objects.get_or_create(
                user=user,
                name=sequence_data['name'],
                defaults=sequence_data
            )
            created_sequences.append(sequence)
            if created:
                self.stdout.write(f'Created sequence: {sequence.name}')
        
        # Add steps to sequences
        if created_sequences and created_templates:
            # Welcome Series steps
            welcome_sequence = created_sequences[0]
            EmailSequenceStep.objects.get_or_create(
                sequence=welcome_sequence,
                step_number=1,
                defaults={
                    'template': created_templates[0],  # Welcome Email
                    'delay_days': 0,
                    'send_only_if_not_replied': True,
                    'is_active': True
                }
            )
            EmailSequenceStep.objects.get_or_create(
                sequence=welcome_sequence,
                step_number=2,
                defaults={
                    'template': created_templates[1],  # Follow-up Email
                    'delay_days': 3,
                    'send_only_if_not_replied': True,
                    'is_active': True
                }
            )
            EmailSequenceStep.objects.get_or_create(
                sequence=welcome_sequence,
                step_number=3,
                defaults={
                    'template': created_templates[2],  # Case Study
                    'delay_days': 7,
                    'send_only_if_not_replied': True,
                    'is_active': True
                }
            )
            
            # Follow-up Series steps
            followup_sequence = created_sequences[1]
            EmailSequenceStep.objects.get_or_create(
                sequence=followup_sequence,
                step_number=1,
                defaults={
                    'template': created_templates[1],  # Follow-up Email
                    'delay_days': 1,
                    'send_only_if_not_replied': True,
                    'is_active': True
                }
            )
            EmailSequenceStep.objects.get_or_create(
                sequence=followup_sequence,
                step_number=2,
                defaults={
                    'template': created_templates[2],  # Case Study
                    'delay_days': 5,
                    'send_only_if_not_replied': True,
                    'is_active': True
                }
            )
            EmailSequenceStep.objects.get_or_create(
                sequence=followup_sequence,
                step_number=3,
                defaults={
                    'template': created_templates[3],  # Special Offer
                    'delay_days': 10,
                    'send_only_if_not_replied': True,
                    'is_active': True
                }
            )
            
            self.stdout.write('Added steps to sequences')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created sample email sequences and templates')
        )
        self.stdout.write(f'Created {len(created_templates)} templates')
        self.stdout.write(f'Created {len(created_sequences)} sequences')
        self.stdout.write('You can now test the email sequences functionality!')
