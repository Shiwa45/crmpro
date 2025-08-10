from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from .models import Lead, LeadSource, LeadActivity
from .forms import LeadCreateForm, LeadUpdateForm, LeadActivityForm, LeadSearchForm
import csv
from datetime import datetime

User = get_user_model()

class LeadListView(LoginRequiredMixin, ListView):
    """List all leads with filtering and search"""
    model = Lead
    template_name = 'leads/lead_list.html'
    context_object_name = 'leads'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter leads based on user role and search parameters"""
        queryset = Lead.objects.select_related('source', 'assigned_to', 'created_by')
        
        # Filter by user role
        if self.request.user.role == 'sales_rep':
            queryset = queryset.filter(assigned_to=self.request.user)
        elif self.request.user.role == 'sales_manager':
            # Sales managers can see their team's leads
            team_members = User.objects.filter(role='sales_rep', department=self.request.user.department)
            queryset = queryset.filter(Q(assigned_to=self.request.user) | Q(assigned_to__in=team_members))
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(company__icontains=search) |
                Q(phone__icontains=search)
            )
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by priority
        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Filter by source
        source = self.request.GET.get('source')
        if source:
            queryset = queryset.filter(source_id=source)
        
        # Filter by assigned user
        assigned_to = self.request.GET.get('assigned_to')
        if assigned_to and self.request.user.role in ['admin', 'sales_manager', 'superadmin']:
            queryset = queryset.filter(assigned_to_id=assigned_to)
        
        # Date range filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lead_sources'] = LeadSource.objects.filter(is_active=True)
        context['status_choices'] = Lead.STATUS_CHOICES
        context['priority_choices'] = Lead.PRIORITY_CHOICES
        context['search_form'] = LeadSearchForm(self.request.GET)
        
        # Add sales reps for admin/manager filter
        if self.request.user.role in ['admin', 'sales_manager', 'superadmin']:
            context['sales_reps'] = User.objects.filter(role='sales_rep', is_active=True)
        
        # Add statistics
        queryset = self.get_queryset()
        context['total_leads'] = queryset.count()
        context['hot_leads'] = queryset.filter(priority='hot').count()
        context['new_leads'] = queryset.filter(status='new').count()
        
        return context

class LeadCreateView(LoginRequiredMixin, CreateView):
    """Create new lead"""
    model = Lead
    form_class = LeadCreateForm
    template_name = 'leads/lead_create.html'
    success_url = reverse_lazy('leads:list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        """Set creator and assigned user"""
        form.instance.created_by = self.request.user
        
        # Auto-assign to current user if not specified
        if not form.instance.assigned_to:
            form.instance.assigned_to = self.request.user
        
        messages.success(self.request, f'Lead {form.instance.get_full_name()} created successfully!')
        
        # Create initial activity log
        response = super().form_valid(form)
        LeadActivity.objects.create(
            lead=self.object,
            user=self.request.user,
            activity_type='note',
            subject='Lead Created',
            description=f'New lead created by {self.request.user.get_full_name()}'
        )
        
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class LeadDetailView(LoginRequiredMixin, DetailView):
    """View lead details"""
    model = Lead
    template_name = 'leads/lead_detail.html'
    context_object_name = 'lead'
    
    def get_queryset(self):
        """Filter leads based on user permissions"""
        queryset = Lead.objects.select_related('source', 'assigned_to', 'created_by')
        
        if self.request.user.role == 'sales_rep':
            return queryset.filter(assigned_to=self.request.user)
        elif self.request.user.role == 'sales_manager':
            team_members = User.objects.filter(role='sales_rep', department=self.request.user.department)
            return queryset.filter(Q(assigned_to=self.request.user) | Q(assigned_to__in=team_members))
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get activities
        context['activities'] = self.object.activities.select_related('user').order_by('-created_at')[:20]
        context['activity_form'] = LeadActivityForm()
        
        # Check permissions for editing
        context['can_edit'] = self.can_edit_lead()
        
        # Lead statistics
        context['total_activities'] = self.object.activities.count()
        
        return context
    
    def can_edit_lead(self):
        """Check if current user can edit this lead"""
        lead = self.get_object()
        user = self.request.user
        
        if user.role in ['admin', 'superadmin']:
            return True
        elif user.role == 'sales_manager':
            return lead.assigned_to.department == user.department
        elif user.role == 'sales_rep':
            return lead.assigned_to == user
        
        return False

class LeadUpdateView(LoginRequiredMixin, UpdateView):
    """Update lead"""
    model = Lead
    form_class = LeadUpdateForm
    template_name = 'leads/lead_update.html'
    
    def get_queryset(self):
        """Filter leads based on user permissions"""
        queryset = Lead.objects.all()
        
        if self.request.user.role == 'sales_rep':
            return queryset.filter(assigned_to=self.request.user)
        elif self.request.user.role == 'sales_manager':
            team_members = User.objects.filter(role='sales_rep', department=self.request.user.department)
            return queryset.filter(Q(assigned_to=self.request.user) | Q(assigned_to__in=team_members))
        
        return queryset
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        """Log status changes and update lead"""
        # Get old values before saving
        old_lead = Lead.objects.get(pk=self.object.pk)
        old_status = old_lead.status
        old_priority = old_lead.priority
        old_assigned_to = old_lead.assigned_to
        
        response = super().form_valid(form)
        
        # Log changes
        changes = []
        
        if old_status != self.object.status:
            changes.append(f'Status changed from {old_lead.get_status_display()} to {self.object.get_status_display()}')
            LeadActivity.objects.create(
                lead=self.object,
                user=self.request.user,
                activity_type='status_change',
                subject=f'Status changed to {self.object.get_status_display()}',
                description=f'Status updated by {self.request.user.get_full_name()}'
            )
        
        if old_priority != self.object.priority:
            changes.append(f'Priority changed from {old_lead.get_priority_display()} to {self.object.get_priority_display()}')
            LeadActivity.objects.create(
                lead=self.object,
                user=self.request.user,
                activity_type='note',
                subject=f'Priority changed to {self.object.get_priority_display()}',
                description=f'Priority updated by {self.request.user.get_full_name()}'
            )
        
        if old_assigned_to != self.object.assigned_to:
            old_name = old_assigned_to.get_full_name() if old_assigned_to else 'Unassigned'
            new_name = self.object.assigned_to.get_full_name() if self.object.assigned_to else 'Unassigned'
            changes.append(f'Assigned from {old_name} to {new_name}')
            LeadActivity.objects.create(
                lead=self.object,
                user=self.request.user,
                activity_type='assignment',
                subject=f'Lead assigned to {new_name}',
                description=f'Assignment updated by {self.request.user.get_full_name()}'
            )
        
        if changes:
            messages.success(self.request, f'Lead updated successfully! Changes: {", ".join(changes)}')
        else:
            messages.success(self.request, 'Lead updated successfully!')
        
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse('leads:detail', kwargs={'pk': self.object.pk})

class LeadDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete lead"""
    model = Lead
    template_name = 'leads/lead_confirm_delete.html'
    success_url = reverse_lazy('leads:list')
    
    def test_func(self):
        """Check if user can delete this lead"""
        lead = self.get_object()
        user = self.request.user
        
        if user.role in ['admin', 'superadmin']:
            return True
        elif user.role == 'sales_manager':
            return lead.assigned_to.department == user.department
        elif user.role == 'sales_rep':
            return lead.assigned_to == user
        
        return False
    
    def delete(self, request, *args, **kwargs):
        lead = self.get_object()
        lead_name = lead.get_full_name()
        
        messages.success(request, f'Lead {lead_name} has been deleted successfully!')
        return super().delete(request, *args, **kwargs)

@login_required
def add_activity(request, pk):
    """Add activity to a lead"""
    lead = get_object_or_404(Lead, pk=pk)
    
    # Check permissions
    user = request.user
    can_add_activity = False
    
    if user.role in ['admin', 'superadmin']:
        can_add_activity = True
    elif user.role == 'sales_manager':
        can_add_activity = lead.assigned_to.department == user.department
    elif user.role == 'sales_rep':
        can_add_activity = lead.assigned_to == user
    
    if not can_add_activity:
        messages.error(request, 'You do not have permission to add activities to this lead.')
        return redirect('leads:detail', pk=pk)
    
    if request.method == 'POST':
        form = LeadActivityForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.lead = lead
            activity.user = request.user
            activity.save()
            
            # Update last contacted if it's a contact activity
            if activity.activity_type in ['call', 'email', 'meeting']:
                lead.last_contacted = timezone.now()
                lead.save()
            
            messages.success(request, 'Activity added successfully!')
        else:
            messages.error(request, 'Error adding activity. Please check the form.')
    
    return redirect('leads:detail', pk=pk)

@login_required
def export_leads(request):
    """Export leads to CSV"""
    # Get filtered queryset based on current user's permissions
    if request.user.role == 'sales_rep':
        leads = Lead.objects.filter(assigned_to=request.user)
    elif request.user.role == 'sales_manager':
        team_members = User.objects.filter(role='sales_rep', department=request.user.department)
        leads = Lead.objects.filter(Q(assigned_to=request.user) | Q(assigned_to__in=team_members))
    else:
        leads = Lead.objects.all()
    
    # Apply same filters as in list view
    search = request.GET.get('search')
    if search:
        leads = leads.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(company__icontains=search) |
            Q(phone__icontains=search)
        )
    
    status = request.GET.get('status')
    if status:
        leads = leads.filter(status=status)
    
    priority = request.GET.get('priority')
    if priority:
        leads = leads.filter(priority=priority)
    
    source = request.GET.get('source')
    if source:
        leads = leads.filter(source_id=source)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="leads_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Name', 'Email', 'Phone', 'Company', 'Job Title', 'Status', 'Priority', 
        'Source', 'Assigned To', 'Budget', 'City', 'State', 'Country',
        'Created Date', 'Last Contacted', 'Requirements'
    ])
    
    # Write data
    for lead in leads.select_related('source', 'assigned_to'):
        writer.writerow([
            lead.get_full_name(),
            lead.email,
            lead.phone or '',
            lead.company or '',
            lead.job_title or '',
            lead.get_status_display(),
            lead.get_priority_display(),
            lead.source.name if lead.source else '',
            lead.assigned_to.get_full_name() if lead.assigned_to else '',
            f'₹{lead.budget}' if lead.budget else '',
            lead.city or '',
            lead.state or '',
            lead.country,
            lead.created_at.strftime('%Y-%m-%d %H:%M'),
            lead.last_contacted.strftime('%Y-%m-%d %H:%M') if lead.last_contacted else '',
            lead.requirements or ''
        ])
    
    return response

@login_required
def lead_stats_api(request):
    """API endpoint for lead statistics"""
    # Get leads based on user permissions
    if request.user.role == 'sales_rep':
        leads = Lead.objects.filter(assigned_to=request.user)
    elif request.user.role == 'sales_manager':
        team_members = User.objects.filter(role='sales_rep', department=request.user.department)
        leads = Lead.objects.filter(Q(assigned_to=request.user) | Q(assigned_to__in=team_members))
    else:
        leads = Lead.objects.all()
    
    # Calculate statistics
    stats = {
        'total': leads.count(),
        'new': leads.filter(status='new').count(),
        'contacted': leads.filter(status='contacted').count(),
        'qualified': leads.filter(status='qualified').count(),
        'won': leads.filter(status='won').count(),
        'lost': leads.filter(status='lost').count(),
        'hot': leads.filter(priority='hot').count(),
        'warm': leads.filter(priority='warm').count(),
        'cold': leads.filter(priority='cold').count(),
    }
    
    # Calculate conversion rate
    if stats['total'] > 0:
        stats['conversion_rate'] = round((stats['won'] / stats['total']) * 100, 2)
    else:
        stats['conversion_rate'] = 0
    
    return JsonResponse(stats)

@login_required
def bulk_update_leads(request):
    """Bulk update multiple leads"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    lead_ids = request.POST.getlist('lead_ids[]')
    action = request.POST.get('action')
    
    if not lead_ids:
        return JsonResponse({'success': False, 'message': 'No leads selected'})
    
    # Get leads that user can modify
    if request.user.role == 'sales_rep':
        leads = Lead.objects.filter(id__in=lead_ids, assigned_to=request.user)
    elif request.user.role == 'sales_manager':
        team_members = User.objects.filter(role='sales_rep', department=request.user.department)
        leads = Lead.objects.filter(
            id__in=lead_ids,
            assigned_to__in=[request.user] + list(team_members)
        )
    else:
        leads = Lead.objects.filter(id__in=lead_ids)
    
    if not leads.exists():
        return JsonResponse({'success': False, 'message': 'No leads found or permission denied'})
    
    updated_count = 0
    
    if action == 'change_status':
        new_status = request.POST.get('new_status')
        if new_status in dict(Lead.STATUS_CHOICES):
            leads.update(status=new_status, updated_at=timezone.now())
            updated_count = leads.count()
            
            # Log activities for each lead
            for lead in leads:
                LeadActivity.objects.create(
                    lead=lead,
                    user=request.user,
                    activity_type='status_change',
                    subject=f'Bulk status change to {dict(Lead.STATUS_CHOICES)[new_status]}',
                    description=f'Status updated via bulk action by {request.user.get_full_name()}'
                )
    
    elif action == 'change_priority':
        new_priority = request.POST.get('new_priority')
        if new_priority in dict(Lead.PRIORITY_CHOICES):
            leads.update(priority=new_priority, updated_at=timezone.now())
            updated_count = leads.count()
    
    elif action == 'assign_to':
        new_assignee_id = request.POST.get('new_assignee')
        try:
            new_assignee = User.objects.get(id=new_assignee_id, role='sales_rep', is_active=True)
            leads.update(assigned_to=new_assignee, updated_at=timezone.now())
            updated_count = leads.count()
            
            # Log activities for each lead
            for lead in leads:
                LeadActivity.objects.create(
                    lead=lead,
                    user=request.user,
                    activity_type='assignment',
                    subject=f'Bulk assignment to {new_assignee.get_full_name()}',
                    description=f'Lead assigned via bulk action by {request.user.get_full_name()}'
                )
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Invalid assignee selected'})
    
    return JsonResponse({
        'success': True, 
        'message': f'Successfully updated {updated_count} leads',
        'updated_count': updated_count
    })

@login_required
def lead_activity_list(request, pk):
    """Get lead activities via AJAX"""
    lead = get_object_or_404(Lead, pk=pk)
    
    # Check permissions
    user = request.user
    can_view = False
    
    if user.role in ['admin', 'superadmin']:
        can_view = True
    elif user.role == 'sales_manager':
        can_view = lead.assigned_to.department == user.department
    elif user.role == 'sales_rep':
        can_view = lead.assigned_to == user
    
    if not can_view:
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    activities = lead.activities.select_related('user').order_by('-created_at')
    
    activity_data = []
    for activity in activities:
        activity_data.append({
            'id': activity.id,
            'type': activity.get_activity_type_display(),
            'subject': activity.subject,
            'description': activity.description,
            'user': activity.user.get_full_name(),
            'created_at': activity.created_at.strftime('%Y-%m-%d %H:%M'),
        })
    
    return JsonResponse({'success': True, 'activities': activity_data})