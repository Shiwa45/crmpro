# Create a management command to setup initial data
# accounts/management/commands/setup_initial_data.py
import os
from django.core.management.base import BaseCommand
from leads.models import LeadSource

class Command(BaseCommand):
    help = 'Setup initial data for CRM'
    
    def handle(self, *args, **options):
        # Create Lead Sources
        sources = [
            'Website Contact Form',
            'Facebook Ads',
            'Google Ads',
            'IndiaMART',
            'Referral',
            'Cold Call',
            'Email Campaign',
            'Trade Show',
            'Social Media',
            'Direct Visit'
        ]
        
        for source_name in sources:
            LeadSource.objects.get_or_create(
                name=source_name,
                defaults={'description': f'Leads from {source_name}'}
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {len(sources)} lead sources')
        )