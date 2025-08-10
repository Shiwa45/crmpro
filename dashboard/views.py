from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, UpdateView
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from datetime import datetime, timedelta, date
from calendar import monthrange
import json
import csv

from leads.models import Lead, LeadSource, LeadActivity
from django.contrib.auth import get_user_model
from .models import DashboardWidget, DashboardPreference, KPITarget, NotificationPreference
from .forms import DashboardFilterForm, ReportGeneratorForm, KPITargetForm, DashboardPreferenceForm

User = get_user_model()

class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view with overview statistics"""
    template_name = 'dashboard/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's dashboard preferences
        preferences, created = DashboardPreference.objects.get_or_create(user=user)
        
        # Get date range from request or preferences
        date_range = self.request.GET.get('date_range', preferences.default_date_range)
        date_from, date_to = self.get_date_range(date_range)
        
        # Get leads queryset based on user role
        leads_queryset = self.get_user_leads_queryset(user, date_from, date_to)
        
        # Calculate comprehensive statistics
        stats = self.calculate_dashboard_stats(leads_queryset, user)
        
        # Get recent activities
        recent_activities = self.get_recent_activities(user)
        
        # Get recent leads
        recent_leads = leads_queryset.select_related(
            'source', 'assigned_to'
        ).order_by('-created_at')[:10]
        
        # Get lead sources with counts
        lead_sources = self.get_lead_sources_data(leads_queryset)
        
        # Get top performers (for managers and admins)
        top_performers = self.get_top_performers(user, date_from, date_to)
        
        # Get overdue leads
        overdue_leads = self.get_overdue_leads(user)
        
        # Get KPI targets
        kpi_targets = self.get_kpi_targets(user, date_from, date_to)
        
        # Get conversion funnel data
        funnel_data = self.get_conversion_funnel(leads_queryset)
        
        context.update({
            'stats': stats,
            'recent_activities': recent_activities,
            'recent_leads': recent_leads,
            'lead_sources': lead_sources,
            'top_performers': top_performers,
            'overdue_leads': overdue_leads,
            'kpi_targets': kpi_targets,
            'funnel_data': funnel_data,
            'user_role': user.role,
            'preferences': preferences,
            'date_range': date_range,
            'date_from': date_from,
            'date_to': date_to,
        })
        
        return context
    
    def get_date_range(self, range_type):
        """Calculate date range based on type"""
        today = timezone.now().date()
        
        if range_type == 'today':
            return today, today
        elif range_type == 'week':
            week_start = today - timedelta(days=today.weekday())
            return week_start, today
        elif range_type == 'month':
            month_start = today.replace(day=1)
            return month_start, today
        elif range_type == 'quarter':
            quarter = (today.month - 1) // 3 + 1
            quarter_start = date(today.year, (quarter - 1) * 3 + 1, 1)
            return quarter_start, today
        elif range_type == 'year':
            year_start = date(today.year, 1, 1)
            return year_start, today
        else:
            # Default to month
            month_start = today.replace(day=1)
            return month_start, today
    
    def get_user_leads_queryset(self, user, date_from=None, date_to=None):
        """Get leads queryset based on user role and date range"""
        if user.role == 'sales_rep':
            queryset = Lead.objects.filter(assigned_to=user)
        elif user.role == 'sales_manager':
            team_members = User.objects.filter(
                role='sales_rep', 
                department=user.department, 
                is_active=True
            )
            queryset = Lead.objects.filter(
                Q(assigned_to=user) | Q(assigned_to__in=team_members)
            )
        else:
            queryset = Lead.objects.all()
        
        if date_from and date_to:
            queryset = queryset.filter(
                created_at__date__gte=date_from,
                created_at__date__lte=date_to
            )
        
        return queryset
    
    def calculate_dashboard_stats(self, leads_queryset, user):
        """Calculate comprehensive dashboard statistics"""
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Basic counts
        total_leads = leads_queryset.count()
        new_leads = leads_queryset.filter(status='new').count()
        contacted_leads = leads_queryset.filter(status='contacted').count()
        qualified_leads = leads_queryset.filter(status='qualified').count()
        won_leads = leads_queryset.filter(status='won').count()
        lost_leads = leads_queryset.filter(status='lost').count()
        
        # Priority counts
        hot_leads = leads_queryset.filter(priority='hot').count()
        warm_leads = leads_queryset.filter(priority='warm').count()
        cold_leads = leads_queryset.filter(priority='cold').count()
        
        # Time-based counts
        today_leads = leads_queryset.filter(created_at__date=today).count()
        week_leads = leads_queryset.filter(created_at__date__gte=week_start).count()
        month_leads = leads_queryset.filter(created_at__date__gte=month_start).count()
        
        # Conversion rates
        conversion_rate = (won_leads / total_leads * 100) if total_leads > 0 else 0
        hot_conversion_rate = (
            leads_queryset.filter(priority='hot', status='won').count() / 
            hot_leads * 100
        ) if hot_leads > 0 else 0
        
        # Revenue calculations
        total_revenue = leads_queryset.filter(status='won').aggregate(
            total=Sum('budget')
        )['total'] or 0
        
        potential_revenue = leads_queryset.exclude(status__in=['won', 'lost']).aggregate(
            total=Sum('budget')
        )['total'] or 0
        
        # Average deal size
        avg_deal_size = leads_queryset.filter(status='won').aggregate(
            avg=Avg('budget')
        )['avg'] or 0
        
        # Overdue leads
        overdue_date = timezone.now() - timedelta(days=7)
        overdue_leads_count = leads_queryset.filter(
            Q(last_contacted__lt=overdue_date) | Q(last_contacted__isnull=True),
            status__in=['new', 'contacted', 'qualified']
        ).count()
        
        return {
            'total_leads': total_leads,
            'new_leads': new_leads,
            'contacted_leads': contacted_leads,
            'qualified_leads': qualified_leads,
            'won_leads': won_leads,
            'lost_leads': lost_leads,
            'hot_leads': hot_leads,
            'warm_leads': warm_leads,
            'cold_leads': cold_leads,
            'today_leads': today_leads,
            'week_leads': week_leads,
            'month_leads': month_leads,
            'conversion_rate': round(conversion_rate, 1),
            'hot_conversion_rate': round(hot_conversion_rate, 1),
            'total_revenue': total_revenue,
            'potential_revenue': potential_revenue,
            'avg_deal_size': round(avg_deal_size, 2),
            'overdue_leads': overdue_leads_count,
        }
    
    def get_recent_activities(self, user):
        """Get recent activities based on user role"""
        if user.role == 'sales_rep':
            activities = LeadActivity.objects.filter(
                lead__assigned_to=user
            ).select_related('lead', 'user').order_by('-created_at')[:10]
        elif user.role == 'sales_manager':
            team_members = User.objects.filter(
                role='sales_rep', 
                department=user.department, 
                is_active=True
            )
            activities = LeadActivity.objects.filter(
                Q(lead__assigned_to=user) | Q(lead__assigned_to__in=team_members)
            ).select_related('lead', 'user').order_by('-created_at')[:10]
        else:
            activities = LeadActivity.objects.select_related(
                'lead', 'user'
            ).order_by('-created_at')[:10]
        
        return activities
    
    def get_lead_sources_data(self, leads_queryset):
        """Get lead sources with performance data"""
        sources = LeadSource.objects.annotate(
            lead_count=Count('lead', filter=Q(lead__in=leads_queryset)),
            won_count=Count('lead', filter=Q(
                lead__in=leads_queryset, 
                lead__status='won'
            ))
        ).filter(
            is_active=True, 
            lead_count__gt=0
        ).order_by('-lead_count')[:5]
        
        # Calculate conversion percentage for each source
        for source in sources:
            if source.lead_count > 0:
                source.conversion_percentage = round((source.won_count / source.lead_count) * 100, 1)
            else:
                source.conversion_percentage = 0
        
        return sources
    
    def get_top_performers(self, user, date_from, date_to):
        """Get top performing sales reps"""
        if user.role not in ['admin', 'sales_manager', 'superadmin']:
            return []
        
        if user.role == 'sales_manager':
            team_users = User.objects.filter(
                role='sales_rep', 
                department=user.department, 
                is_active=True
            )
        else:
            team_users = User.objects.filter(
                role='sales_rep', 
                is_active=True
            )
        
        performers = team_users.annotate(
            total_leads=Count('assigned_leads', filter=Q(
                assigned_leads__created_at__date__gte=date_from,
                assigned_leads__created_at__date__lte=date_to
            )),
            won_leads=Count('assigned_leads', filter=Q(
                assigned_leads__created_at__date__gte=date_from,
                assigned_leads__created_at__date__lte=date_to,
                assigned_leads__status='won'
            )),
            revenue=Sum('assigned_leads__budget', filter=Q(
                assigned_leads__created_at__date__gte=date_from,
                assigned_leads__created_at__date__lte=date_to,
                assigned_leads__status='won'
            ))
        ).order_by('-won_leads')[:5]
        
        # Calculate conversion rates
        for performer in performers:
            if performer.total_leads > 0:
                performer.conversion_rate = round(
                    (performer.won_leads / performer.total_leads * 100), 1
                )
            else:
                performer.conversion_rate = 0
            
            performer.revenue = performer.revenue or 0
        
        return performers
    
    def get_overdue_leads(self, user):
        """Get overdue leads that need follow-up"""
        overdue_date = timezone.now() - timedelta(days=7)
        
        if user.role == 'sales_rep':
            queryset = Lead.objects.filter(assigned_to=user)
        elif user.role == 'sales_manager':
            team_members = User.objects.filter(
                role='sales_rep', 
                department=user.department, 
                is_active=True
            )
            queryset = Lead.objects.filter(
                Q(assigned_to=user) | Q(assigned_to__in=team_members)
            )
        else:
            queryset = Lead.objects.all()
        
        return queryset.filter(
            Q(last_contacted__lt=overdue_date) | Q(last_contacted__isnull=True),
            status__in=['new', 'contacted', 'qualified']
        ).select_related('assigned_to').order_by('created_at')[:10]
    
    def get_kpi_targets(self, user, date_from, date_to):
        """Get KPI targets for the user"""
        return KPITarget.objects.filter(
            user=user,
            period_start__lte=date_to,
            period_end__gte=date_from,
            is_active=True
        )
    
    def get_conversion_funnel(self, leads_queryset):
        """Get conversion funnel data"""
        total = leads_queryset.count()
        contacted = leads_queryset.filter(
            status__in=['contacted', 'qualified', 'proposal', 'negotiation', 'won']
        ).count()
        qualified = leads_queryset.filter(
            status__in=['qualified', 'proposal', 'negotiation', 'won']
        ).count()
        proposal = leads_queryset.filter(
            status__in=['proposal', 'negotiation', 'won']
        ).count()
        won = leads_queryset.filter(status='won').count()
        
        return [
            {
                'stage': 'Total Leads',
                'count': total,
                'percentage': 100,
                'color': '#6c757d'
            },
            {
                'stage': 'Contacted',
                'count': contacted,
                'percentage': round((contacted/total*100), 1) if total > 0 else 0,
                'color': '#0d6efd'
            },
            {
                'stage': 'Qualified',
                'count': qualified,
                'percentage': round((qualified/total*100), 1) if total > 0 else 0,
                'color': '#fd7e14'
            },
            {
                'stage': 'Proposal',
                'count': proposal,
                'percentage': round((proposal/total*100), 1) if total > 0 else 0,
                'color': '#ffc107'
            },
            {
                'stage': 'Won',
                'count': won,
                'percentage': round((won/total*100), 1) if total > 0 else 0,
                'color': '#198754'
            },
        ]

class AnalyticsView(LoginRequiredMixin, TemplateView):
    """Advanced analytics and reporting dashboard"""
    template_name = 'dashboard/analytics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get date range from request
        date_range = self.request.GET.get('date_range', 'month')
        custom_from = self.request.GET.get('date_from')
        custom_to = self.request.GET.get('date_to')
        
        if date_range == 'custom' and custom_from and custom_to:
            date_from = datetime.strptime(custom_from, '%Y-%m-%d').date()
            date_to = datetime.strptime(custom_to, '%Y-%m-%d').date()
        else:
            dashboard_view = DashboardView()
            date_from, date_to = dashboard_view.get_date_range(date_range)
        
        # Get leads queryset
        dashboard_view = DashboardView()
        leads_queryset = dashboard_view.get_user_leads_queryset(user, date_from, date_to)
        
        # Get all analytics data
        monthly_data = self.get_monthly_data(leads_queryset)
        status_data = self.get_status_distribution(leads_queryset)
        source_data = self.get_source_performance(leads_queryset)
        team_data = self.get_team_performance(user, date_from, date_to)
        
        context.update({
            'monthly_data': monthly_data,
            'status_data': status_data,
            'source_data': source_data,
            'team_data': team_data,
            'user_role': user.role,
            'date_range': date_range,
            'date_from': date_from,
            'date_to': date_to,
        })
        
        return context
    
    def get_monthly_data(self, leads_queryset):
        """Get monthly lead statistics for the last 6 months"""
        monthly_data = []
        now = timezone.now()
        
        for i in range(6):
            if i == 0:
                month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                month_end = now
            else:
                year = now.year
                month = now.month - i
                if month <= 0:
                    month += 12
                    year -= 1
                
                month_start = datetime(year, month, 1)
                month_start = timezone.make_aware(month_start)
                
                last_day = monthrange(year, month)[1]
                month_end = datetime(year, month, last_day, 23, 59, 59)
                month_end = timezone.make_aware(month_end)
            
            month_leads = leads_queryset.filter(
                created_at__gte=month_start,
                created_at__lte=month_end
            )
            
            total_count = month_leads.count()
            won_count = month_leads.filter(status='won').count()
            lost_count = month_leads.filter(status='lost').count()
            
            monthly_data.append({
                'month': month_start.strftime('%B %Y'),
                'month_short': month_start.strftime('%b %Y'),
                'total': total_count,
                'won': won_count,
                'lost': lost_count,
                'in_progress': total_count - won_count - lost_count,
                'conversion_rate': round((won_count / total_count * 100), 1) if total_count > 0 else 0,
            })
        
        return list(reversed(monthly_data))
    
    def get_status_distribution(self, leads_queryset):
        """Get lead status distribution"""
        status_data = []
        total_leads = leads_queryset.count()
        
        for status_value, status_label in Lead.STATUS_CHOICES:
            count = leads_queryset.filter(status=status_value).count()
            if count > 0:
                percentage = round((count / total_leads * 100), 1) if total_leads > 0 else 0
                status_data.append({
                    'status': status_label,
                    'status_value': status_value,
                    'count': count,
                    'percentage': percentage,
                })
        
        return status_data
    
    def get_source_performance(self, leads_queryset):
        """Get lead source performance"""
        source_data = LeadSource.objects.annotate(
            total_leads=Count('lead', filter=Q(lead__in=leads_queryset)),
            won_leads=Count('lead', filter=Q(
                lead__in=leads_queryset, 
                lead__status='won'
            ))
        ).filter(total_leads__gt=0).order_by('-total_leads')
        
        for source in source_data:
            if source.total_leads > 0:
                source.conversion_rate = round(
                    (source.won_leads / source.total_leads * 100), 1
                )
            else:
                source.conversion_rate = 0
        
        return source_data
    
    def get_team_performance(self, user, date_from, date_to):
        """Get team performance data"""
        team_data = []
        
        if user.role in ['admin', 'sales_manager', 'superadmin']:
            if user.role == 'sales_manager':
                team_users = User.objects.filter(
                    role='sales_rep', 
                    department=user.department, 
                    is_active=True
                )
            else:
                team_users = User.objects.filter(
                    role='sales_rep', 
                    is_active=True
                )
            
            team_data = team_users.annotate(
                total_leads=Count('assigned_leads', filter=Q(
                    assigned_leads__created_at__date__gte=date_from,
                    assigned_leads__created_at__date__lte=date_to
                )),
                won_leads=Count('assigned_leads', filter=Q(
                    assigned_leads__created_at__date__gte=date_from,
                    assigned_leads__created_at__date__lte=date_to,
                    assigned_leads__status='won'
                ))
            ).order_by('-won_leads')
            
            for member in team_data:
                if member.total_leads > 0:
                    member.conversion_rate = round(
                        (member.won_leads / member.total_leads * 100), 1
                    )
                else:
                    member.conversion_rate = 0
        
        return team_data

class ReportsView(LoginRequiredMixin, TemplateView):
    """Generate and download reports"""
    template_name = 'dashboard/reports.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_form'] = ReportGeneratorForm()
        return context

class DashboardPreferenceView(LoginRequiredMixin, UpdateView):
    """Update dashboard preferences"""
    model = DashboardPreference
    form_class = DashboardPreferenceForm
    template_name = 'dashboard/preferences.html'
    success_url = '/dashboard/'
    
    def get_object(self):
        obj, created = DashboardPreference.objects.get_or_create(user=self.request.user)
        return obj

@login_required
def dashboard_api_stats(request):
    """API endpoint for real-time dashboard statistics"""
    user = request.user
    
    dashboard_view = DashboardView()
    date_range = request.GET.get('date_range', 'month')
    date_from, date_to = dashboard_view.get_date_range(date_range)
    
    leads_queryset = dashboard_view.get_user_leads_queryset(user, date_from, date_to)
    stats = dashboard_view.calculate_dashboard_stats(leads_queryset, user)
    
    return JsonResponse(stats)

@login_required
def dashboard_chart_data(request):
    """API endpoint for chart data"""
    chart_type = request.GET.get('type', 'monthly')
    user = request.user
    
    dashboard_view = DashboardView()
    analytics_view = AnalyticsView()
    
    date_range = request.GET.get('date_range', 'month')
    date_from, date_to = dashboard_view.get_date_range(date_range)
    
    leads_queryset = dashboard_view.get_user_leads_queryset(user, date_from, date_to)
    
    if chart_type == 'monthly':
        data = analytics_view.get_monthly_data(leads_queryset)
        return JsonResponse({'data': data})
    
    elif chart_type == 'status':
        data = analytics_view.get_status_distribution(leads_queryset)
        return JsonResponse({'data': data})
    
    elif chart_type == 'sources':
        data = list(analytics_view.get_source_performance(leads_queryset).values(
            'name', 'total_leads', 'won_leads', 'conversion_rate'
        ))
        return JsonResponse({'data': data})
    
    elif chart_type == 'funnel':
        data = dashboard_view.get_conversion_funnel(leads_queryset)
        return JsonResponse({'data': data})
    
    return JsonResponse({'error': 'Invalid chart type'})

@login_required
def export_dashboard_report(request):
    """Export dashboard data as CSV"""
    user = request.user
    
    dashboard_view = DashboardView()
    date_range = request.GET.get('date_range', 'month')
    date_from, date_to = dashboard_view.get_date_range(date_range)
    leads_queryset = dashboard_view.get_user_leads_queryset(user, date_from, date_to)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="dashboard_report_{date_from}_{date_to}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Dashboard Report', f'{date_from} to {date_to}'])
    writer.writerow([])
    
    # Write summary statistics
    stats = dashboard_view.calculate_dashboard_stats(leads_queryset, user)
    writer.writerow(['Summary Statistics'])
    writer.writerow(['Total Leads', stats['total_leads']])
    writer.writerow(['Won Leads', stats['won_leads']])
    writer.writerow(['Conversion Rate', f"{stats['conversion_rate']}%"])
    writer.writerow(['Total Revenue', f"₹{stats['total_revenue']:,.2f}"])
    writer.writerow(['Average Deal Size', f"₹{stats['avg_deal_size']:,.2f}"])
    
    # Write monthly data
    analytics_view = AnalyticsView()
    monthly_data = analytics_view.get_monthly_data(leads_queryset)
    
    writer.writerow([])
    writer.writerow(['Monthly Performance'])
    writer.writerow(['Month', 'Total Leads', 'Won', 'Lost', 'Conversion Rate'])
    for month in monthly_data[-6:]:
        writer.writerow([
            month['month_short'],
            month['total'],
            month['won'],
            month['lost'],
            f"{month['conversion_rate']}%"
        ])
    
    # Write source data
    source_data = analytics_view.get_source_performance(leads_queryset)
    
    writer.writerow([])
    writer.writerow(['Lead Source Performance'])
    writer.writerow(['Source', 'Total Leads', 'Won', 'Conversion Rate'])
    for source in source_data[:10]:
        writer.writerow([
            source.name,
            source.total_leads,
            source.won_leads,
            f"{source.conversion_rate}%"
        ])
    
    return response

@login_required
def kpi_targets_view(request):
    """Manage KPI targets"""
    if request.method == 'POST':
        form = KPITargetForm(request.POST)
        if form.is_valid():
            kpi_target = form.save(commit=False)
            kpi_target.user = request.user
            kpi_target.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    
    targets = KPITarget.objects.filter(user=request.user, is_active=True)
    form = KPITargetForm()
    
    return render(request, 'dashboard/kpi_targets.html', {
        'targets': targets,
        'form': form
    })

@login_required
def update_kpi_progress(request):
    """Update KPI progress"""
    if request.method == 'POST':
        target_id = request.POST.get('target_id')
        new_value = request.POST.get('value')
        
        try:
            target = KPITarget.objects.get(id=target_id, user=request.user)
            target.current_value = new_value
            target.save()
            
            return JsonResponse({
                'success': True,
                'completion_percentage': target.completion_percentage,
                'is_achieved': target.is_achieved
            })
        except KPITarget.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Target not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})