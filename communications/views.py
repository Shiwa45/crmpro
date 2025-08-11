# communications/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.http import JsonResponse, HttpResponse, Http404
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
import json

from leads.models import Lead, LeadActivity
from .models import (
    EmailConfiguration, EmailTemplate, EmailCampaign, Email, 
    EmailSequence, EmailSequenceStep, EmailSequenceEnrollment, EmailTracking
)
from .forms import (
    EmailConfigurationForm, EmailTemplateForm, QuickEmailForm, 
    EmailCampaignForm, EmailSequenceForm, EmailSequenceStepForm,
    BulkEmailForm, EmailTestForm, EmailStatsFilterForm
)
from .services import (
    EmailService, EmailTemplateService, EmailCampaignService,
    EmailSequenceService, EmailAnalyticsService
)

# ==============================================================================
# EMAIL CONFIGURATION VIEWS
# ==============================================================================

class EmailConfigurationListView(LoginRequiredMixin, ListView):
    """List user's email configurations"""
    model = EmailConfiguration
    template_name = 'communications/config_list.html'
    context_object_name = 'configs'
    
    def get_queryset(self):
        return EmailConfiguration.objects.filter(user=self.request.user).order_by('-is_default', 'name')

class EmailConfigurationCreateView(LoginRequiredMixin, CreateView):
    """Create new email configuration"""
    model = EmailConfiguration
    form_class = EmailConfigurationForm
    template_name = 'communications/config_form.html'
    success_url = reverse_lazy('communications:config_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Email configuration created successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class EmailConfigurationUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update email configuration"""
    model = EmailConfiguration
    form_class = EmailConfigurationForm
    template_name = 'communications/config_form.html'
    success_url = reverse_lazy('communications:config_list')
    
    def test_func(self):
        return self.get_object().user == self.request.user
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Email configuration updated successfully!')
        return super().form_valid(form)

@login_required
def test_email_config(request, pk):
    """Test email configuration"""
    config = get_object_or_404(EmailConfiguration, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = EmailTestForm(request.POST, email_config=config)
        if form.is_valid():
            test_email = form.cleaned_data['test_email']
            
            email_service = EmailService(config)
            success, message = email_service.send_test_email(test_email)
            
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
            
            return redirect('communications:config_list')
    else:
        form = EmailTestForm(email_config=config)
    
    return render(request, 'communications/test_email.html', {
        'form': form,
        'config': config
    })

# ==============================================================================
# EMAIL TEMPLATE VIEWS
# ==============================================================================

class EmailTemplateListView(LoginRequiredMixin, ListView):
    """List email templates"""
    model = EmailTemplate
    template_name = 'communications/template_list.html'
    context_object_name = 'templates'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = EmailTemplate.objects.filter(
            Q(user=self.request.user) | Q(is_shared=True)
        ).select_related('user')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(subject__icontains=search) |
                Q(template_type__icontains=search)
            )
        
        # Filter by type
        template_type = self.request.GET.get('type')
        if template_type:
            queryset = queryset.filter(template_type=template_type)
        
        return queryset.order_by('-last_used', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['template_types'] = EmailTemplate.TEMPLATE_TYPES
        return context

class EmailTemplateCreateView(LoginRequiredMixin, CreateView):
    """Create new email template"""
    model = EmailTemplate
    form_class = EmailTemplateForm
    template_name = 'communications/template_form.html'
    success_url = reverse_lazy('communications:template_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Email template created successfully!')
        return super().form_valid(form)

class EmailTemplateUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update email template"""
    model = EmailTemplate
    form_class = EmailTemplateForm
    template_name = 'communications/template_form.html'
    success_url = reverse_lazy('communications:template_list')
    
    def test_func(self):
        return self.get_object().user == self.request.user
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Email template updated successfully!')
        return super().form_valid(form)

class EmailTemplateDetailView(LoginRequiredMixin, DetailView):
    """View email template details"""
    model = EmailTemplate
    template_name = 'communications/template_detail.html'
    context_object_name = 'template'
    
    def get_queryset(self):
        return EmailTemplate.objects.filter(
            Q(user=self.request.user) | Q(is_shared=True)
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get template performance stats
        context['stats'] = EmailAnalyticsService.get_template_performance(self.object)
        return context

@login_required
def template_preview(request, pk):
    """Preview email template with sample data"""
    template = get_object_or_404(
        EmailTemplate, 
        pk=pk
    )
    
    # Check permissions
    if not (template.user == request.user or template.is_shared):
        raise Http404("Template not found")
    
    # Create sample lead for preview
    sample_lead = Lead(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        company="Sample Company",
        phone="+1 555-0123"
    )
    
    # Render template with sample data
    rendered = EmailTemplateService.render_template(template, sample_lead, request.user)
    
    return JsonResponse(rendered)

# ==============================================================================
# EMAIL CAMPAIGN VIEWS
# ==============================================================================

class EmailCampaignListView(LoginRequiredMixin, ListView):
    """List email campaigns"""
    model = EmailCampaign
    template_name = 'communications/campaign_list.html'
    context_object_name = 'campaigns'
    paginate_by = 20
    
    def get_queryset(self):
        return EmailCampaign.objects.filter(user=self.request.user).select_related(
            'template', 'email_config'
        ).order_by('-created_at')

class EmailCampaignCreateView(LoginRequiredMixin, CreateView):
    """Create new email campaign"""
    model = EmailCampaign
    form_class = EmailCampaignForm
    template_name = 'communications/campaign_form.html'
    success_url = reverse_lazy('communications:campaign_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        campaign = form.save()
        
        # Create email records for campaign
        emails_created = EmailCampaignService.create_campaign_emails(campaign)
        
        if campaign.send_now:
            campaign.status = 'sending'
            campaign.started_at = timezone.now()
            campaign.save()
            
            # Start sending immediately
            # Note: In production, this should be handled by a background task
            EmailCampaignService.send_campaign_batch(campaign)
        
        messages.success(
            self.request, 
            f'Campaign created with {emails_created} recipients!'
        )
        return super().form_valid(form)

class EmailCampaignDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """View campaign details and statistics"""
    model = EmailCampaign
    template_name = 'communications/campaign_detail.html'
    context_object_name = 'campaign'
    
    def test_func(self):
        return self.get_object().user == self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get campaign statistics
        context['stats'] = EmailAnalyticsService.get_campaign_stats(self.object)
        
        # Get recent emails from this campaign
        context['recent_emails'] = Email.objects.filter(
            campaign=self.object
        ).select_related('lead').order_by('-created_at')[:10]
        
        return context

@login_required
def start_campaign(request, pk):
    """Start a draft campaign"""
    campaign = get_object_or_404(EmailCampaign, pk=pk, user=request.user)
    
    if campaign.status != 'draft':
        messages.error(request, 'Campaign is not in draft status.')
        return redirect('communications:campaign_detail', pk=pk)
    
    if request.method == 'POST':
        campaign.status = 'sending'
        campaign.started_at = timezone.now()
        campaign.save()
        
        # Start sending
        result = EmailCampaignService.send_campaign_batch(campaign)
        
        messages.success(
            request, 
            f'Campaign started! Sent: {result["sent"]}, Failed: {result["failed"]}'
        )
    
    return redirect('communications:campaign_detail', pk=pk)

@login_required
def pause_campaign(request, pk):
    """Pause a running campaign"""
    campaign = get_object_or_404(EmailCampaign, pk=pk, user=request.user)
    
    if campaign.status == 'sending':
        campaign.status = 'paused'
        campaign.save()
        messages.success(request, 'Campaign paused.')
    
    return redirect('communications:campaign_detail', pk=pk)

# ==============================================================================
# QUICK EMAIL VIEWS
# ==============================================================================

@login_required
def send_quick_email(request, lead_id):
    """Send quick email to a lead"""
    lead = get_object_or_404(Lead, pk=lead_id)
    
    # Check permissions
    if request.user.role == 'sales_rep' and lead.assigned_to != request.user:
        messages.error(request, 'You can only email leads assigned to you.')
        return redirect('leads:detail', pk=lead_id)
    
    if request.method == 'POST':
        form = QuickEmailForm(request.POST, user=request.user, lead=lead)
        if form.is_valid():
            # Get or create default email config
            email_config = EmailConfiguration.objects.filter(
                user=request.user, is_default=True
            ).first()
            
            if not email_config:
                email_config = EmailConfiguration.objects.filter(
                    user=request.user, is_active=True
                ).first()
            
            if not email_config:
                messages.error(request, 'Please configure an email account first.')
                return redirect('communications:config_create')
            
            # Create and send email
            email = Email.objects.create(
                user=request.user,
                lead=lead,
                subject=form.cleaned_data['subject'],
                body_html=form.cleaned_data['body_html'],
                from_email=email_config.from_email,
                from_name=email_config.from_name,
                to_email=lead.email,
                to_name=lead.get_full_name(),
                reply_to=email_config.reply_to,
                status='queued'
            )
            
            # Send email
            email_service = EmailService(email_config)
            success, message = email_service.send_email(email)
            
            if success:
                messages.success(request, f'Email sent to {lead.get_full_name()}!')
                
                # Update template usage if template was used
                template = form.cleaned_data.get('template')
                if template:
                    template.usage_count += 1
                    template.last_used = timezone.now()
                    template.save()
            else:
                messages.error(request, f'Failed to send email: {message}')
            
            return redirect('leads:detail', pk=lead_id)
    else:
        form = QuickEmailForm(user=request.user, lead=lead)
    
    return render(request, 'communications/quick_email.html', {
        'form': form,
        'lead': lead
    })

@login_required
def bulk_email(request):
    """Send bulk email to selected leads"""
    if request.method == 'POST':
        form = BulkEmailForm(request.POST, user=request.user)
        if form.is_valid():
            template = form.cleaned_data['template']
            leads = form.cleaned_data['lead_objects']
            
            # Get email config
            email_config = form.cleaned_data.get('email_config')
            if not email_config:
                email_config = EmailConfiguration.objects.filter(
                    user=request.user, is_default=True
                ).first()
            
            if not email_config:
                messages.error(request, 'No email configuration available.')
                return redirect('communications:config_create')
            
            # Create campaign for bulk email
            campaign = EmailCampaign.objects.create(
                name=f"Bulk Email - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                user=request.user,
                template=template,
                email_config=email_config,
                status='sending' if not form.cleaned_data.get('schedule_send') else 'scheduled',
                scheduled_at=form.cleaned_data.get('scheduled_at'),
                target_all_leads=False
            )
            
            # Add specific leads to campaign
            campaign.specific_leads.set(leads)
            
            # Create and send emails
            emails_created = EmailCampaignService.create_campaign_emails(campaign)
            
            if not form.cleaned_data.get('schedule_send'):
                result = EmailCampaignService.send_campaign_batch(campaign)
                messages.success(
                    request, 
                    f'Bulk email sent to {emails_created} leads! '
                    f'Sent: {result["sent"]}, Failed: {result["failed"]}'
                )
            else:
                messages.success(
                    request,
                    f'Bulk email scheduled for {emails_created} leads!'
                )
            
            return redirect('communications:campaign_detail', pk=campaign.pk)
    else:
        # Get lead IDs from URL parameters
        lead_ids = request.GET.get('leads', '').split(',')
        leads_data = json.dumps([int(id) for id in lead_ids if id.isdigit()])
        
        form = BulkEmailForm(user=request.user, initial={'leads': leads_data})
    
    return render(request, 'communications/bulk_email.html', {
        'form': form
    })

# ==============================================================================
# EMAIL SEQUENCE VIEWS
# ==============================================================================

class EmailSequenceListView(LoginRequiredMixin, ListView):
    """List email sequences"""
    model = EmailSequence
    template_name = 'communications/sequence_list.html'
    context_object_name = 'sequences'
    
    def get_queryset(self):
        return EmailSequence.objects.filter(user=self.request.user).prefetch_related(
            'steps', 'emailsequenceenrollment_set'
        )

class EmailSequenceCreateView(LoginRequiredMixin, CreateView):
    """Create new email sequence"""
    model = EmailSequence
    form_class = EmailSequenceForm
    template_name = 'communications/sequence_form.html'
    success_url = reverse_lazy('communications:sequence_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Email sequence created successfully!')
        return super().form_valid(form)

class EmailSequenceDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """View sequence details and manage steps"""
    model = EmailSequence
    template_name = 'communications/sequence_detail.html'
    context_object_name = 'sequence'
    
    def test_func(self):
        return self.get_object().user == self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['steps'] = self.object.steps.all().select_related('template')
        context['enrollments'] = EmailSequenceEnrollment.objects.filter(
            sequence=self.object
        ).select_related('lead').order_by('-enrolled_at')[:10]
        return context

@login_required
def add_sequence_step(request, sequence_id):
    """Add step to email sequence"""
    sequence = get_object_or_404(EmailSequence, pk=sequence_id, user=request.user)
    
    if request.method == 'POST':
        form = EmailSequenceStepForm(
            request.POST, 
            user=request.user, 
            sequence=sequence
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Sequence step added successfully!')
            return redirect('communications:sequence_detail', pk=sequence_id)
    else:
        form = EmailSequenceStepForm(user=request.user, sequence=sequence)
    
    return render(request, 'communications/sequence_step_form.html', {
        'form': form,
        'sequence': sequence
    })

# ==============================================================================
# EMAIL TRACKING AND ANALYTICS VIEWS
# ==============================================================================

@csrf_exempt
@require_http_methods(["GET"])
def email_tracking(request, tracking_id, event):
    """Handle email tracking events"""
    try:
        email = Email.objects.get(tracking_id=tracking_id)
        
        # Create tracking event
        EmailTracking.objects.create(
            email=email,
            event_type=event,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Update email status
        if event == 'opened':
            email.mark_as_opened()
        elif event == 'clicked':
            email.mark_as_clicked()
        
        # Return 1x1 transparent pixel for open tracking
        if event == 'opened':
            response = HttpResponse(
                b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00'
                b'\x00\x00\x00\x21\xF9\x04\x01\x00\x00\x00\x00\x2C\x00\x00\x00\x00'
                b'\x01\x00\x01\x00\x00\x02\x02\x04\x01\x00\x3B',
                content_type='image/gif'
            )
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            return response
    
    except Email.DoesNotExist:
        pass
    
    return HttpResponse(status=204)

@login_required
def email_analytics(request):
    """Email analytics dashboard"""
    user = request.user
    
    # Get date range from form
    form = EmailStatsFilterForm(request.GET, user=user)
    date_from = None
    date_to = None
    
    if form.is_valid():
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
    
    # Get user email statistics
    stats = EmailAnalyticsService.get_user_email_stats(user, date_from, date_to)
    
    # Get recent campaigns
    recent_campaigns = EmailCampaign.objects.filter(
        user=user
    ).order_by('-created_at')[:5]
    
    # Get top performing templates
    top_templates = EmailTemplate.objects.filter(
        Q(user=user) | Q(is_shared=True)
    ).filter(
        usage_count__gt=0
    ).order_by('-usage_count')[:5]
    
    context = {
        'stats': stats,
        'recent_campaigns': recent_campaigns,
        'top_templates': top_templates,
        'form': form,
    }
    
    return render(request, 'communications/analytics.html', context)

@login_required
def email_list(request):
    """List all emails sent by user"""
    emails = Email.objects.filter(user=request.user).select_related(
        'lead', 'template', 'campaign'
    ).order_by('-created_at')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        emails = emails.filter(status=status)
    
    # Filter by lead
    lead_id = request.GET.get('lead')
    if lead_id:
        emails = emails.filter(lead_id=lead_id)
    
    # Filter by campaign
    campaign_id = request.GET.get('campaign')
    if campaign_id:
        emails = emails.filter(campaign_id=campaign_id)
    
    # Pagination
    paginator = Paginator(emails, 25)
    page_number = request.GET.get('page')
    emails = paginator.get_page(page_number)
    
    context = {
        'emails': emails,
        'status_choices': Email.STATUS_CHOICES,
    }
    
    return render(request, 'communications/email_list.html', context)

@login_required
def email_detail(request, pk):
    """View email details"""
    email = get_object_or_404(
        Email, 
        pk=pk, 
        user=request.user
    )
    
    # Get tracking events
    tracking_events = email.tracking_events.all().order_by('-timestamp')
    
    context = {
        'email': email,
        'tracking_events': tracking_events,
    }
    
    return render(request, 'communications/email_detail.html', context)

# ==============================================================================
# API VIEWS FOR AJAX REQUESTS
# ==============================================================================

@login_required
def template_list_api(request):
    """API endpoint for template list (used by quick email form)"""
    templates = EmailTemplate.objects.filter(
        Q(user=request.user) | Q(is_shared=True),
        is_active=True
    ).values('id', 'name', 'subject', 'body_html', 'template_type')
    
    return JsonResponse({'templates': list(templates)})

@login_required
def email_stats_api(request):
    """API endpoint for email statistics"""
    user = request.user
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
    if date_to:
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    stats = EmailAnalyticsService.get_user_email_stats(user, date_from, date_to)
    
    return JsonResponse(stats)

@login_required
def campaign_progress_api(request, pk):
    """API endpoint for campaign progress"""
    campaign = get_object_or_404(EmailCampaign, pk=pk, user=request.user)
    stats = EmailAnalyticsService.get_campaign_stats(campaign)
    
    return JsonResponse({
        'status': campaign.status,
        'progress': {
            'sent': stats['total_sent'],
            'total': campaign.total_recipients,
            'percentage': (stats['total_sent'] / campaign.total_recipients * 100) if campaign.total_recipients > 0 else 0
        },
        'stats': stats
    })

# ==============================================================================
# UTILITY VIEWS
# ==============================================================================

@login_required
def email_preview_api(request):
    """API endpoint for email preview"""
    if request.method == 'POST':
        data = json.loads(request.body)
        subject = data.get('subject', '')
        body_html = data.get('body_html', '')
        lead_id = data.get('lead_id')
        
        if lead_id:
            try:
                lead = Lead.objects.get(pk=lead_id)
                
                # Replace variables with actual lead data
                context = {
                    'lead_name': lead.get_full_name(),
                    'first_name': lead.first_name,
                    'last_name': lead.last_name or '',
                    'company': lead.company or '',
                    'email': lead.email,
                    'phone': lead.phone or '',
                    'user_name': request.user.get_full_name(),
                    'user_email': request.user.email,
                    'current_date': timezone.now().strftime('%B %d, %Y'),
                }
                
                from django.template import Template, Context
                
                subject_template = Template(subject)
                rendered_subject = subject_template.render(Context(context))
                
                html_template = Template(body_html)
                rendered_html = html_template.render(Context(context))
                
                return JsonResponse({
                    'subject': rendered_subject,
                    'html_body': rendered_html
                })
                
            except Lead.DoesNotExist:
                pass
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required 
def dashboard_email_widget(request):
    """Email widget data for dashboard"""
    user = request.user
    
    # Get recent emails
    recent_emails = Email.objects.filter(user=user).select_related(
        'lead'
    ).order_by('-created_at')[:5]
    
    # Get email stats for this week
    week_ago = timezone.now() - timedelta(days=7)
    week_stats = EmailAnalyticsService.get_user_email_stats(
        user, week_ago.date(), timezone.now().date()
    )
    
    data = {
        'recent_emails': [
            {
                'id': email.id,
                'subject': email.subject,
                'lead_name': email.lead.get_full_name(),
                'status': email.status,
                'sent_at': email.sent_at.strftime('%Y-%m-%d %H:%M') if email.sent_at else None,
            }
            for email in recent_emails
        ],
        'week_stats': week_stats
    }
    
    return JsonResponse(data)