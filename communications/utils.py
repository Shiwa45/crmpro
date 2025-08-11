
# communications/utils.py
from django.utils.html import strip_tags
from django.template import Template, Context
import re

def html_to_text(html_content):
    """Convert HTML content to plain text"""
    # Remove script and style elements
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
    
    # Convert line breaks
    html_content = re.sub(r'<br[^>]*>', '\n', html_content)
    html_content = re.sub(r'</p>', '\n\n', html_content)
    html_content = re.sub(r'</div>', '\n', html_content)
    
    # Strip remaining HTML tags
    text = strip_tags(html_content)
    
    # Clean up whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()

def validate_email_template(subject, body_html):
    """Validate email template content"""
    errors = []
    
    if not subject.strip():
        errors.append("Subject cannot be empty")
    
    if len(subject) > 300:
        errors.append("Subject is too long (max 300 characters)")
    
    if not body_html.strip():
        errors.append("Email body cannot be empty")
    
    # Check for common template variables
    template_vars = re.findall(r'\{\{[^}]+\}\}', subject + body_html)
    valid_vars = [
        '{{lead_name}}', '{{first_name}}', '{{last_name}}', '{{company}}',
        '{{email}}', '{{phone}}', '{{user_name}}', '{{user_email}}', '{{current_date}}'
    ]
    
    for var in template_vars:
        if var not in valid_vars:
            errors.append(f"Unknown template variable: {var}")
    
    return errors

def get_email_client_stats(emails_queryset):
    """Get email client statistics from tracking data"""
    # This would analyze User-Agent strings from tracking data
    # For now, return mock data
    return {
        'gmail': 35,
        'outlook': 28,
        'apple_mail': 15,
        'yahoo': 12,
        'other': 10
    }

def calculate_best_send_time(user):
    """Calculate optimal send time based on historical open rates"""
    # This would analyze when emails are typically opened
    # For now, return default best practice time
    return {
        'hour': 10,  # 10 AM
        'day_of_week': 2,  # Tuesday
        'timezone': 'UTC'
    }