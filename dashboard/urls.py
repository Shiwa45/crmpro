from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard pages
    path('', views.DashboardView.as_view(), name='home'),
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),
    
    # API endpoints for AJAX calls
    path('api/stats/', views.dashboard_api_stats, name='api_stats'),
    path('api/chart-data/', views.dashboard_chart_data, name='chart_data'),
    
    # Export endpoints
    path('export/report/', views.export_dashboard_report, name='export_report'),
]