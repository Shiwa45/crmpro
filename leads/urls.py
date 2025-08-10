from django.urls import path
from . import views

app_name = 'leads'

urlpatterns = [
    # Lead CRUD URLs
    path('', views.LeadListView.as_view(), name='list'),
    path('create/', views.LeadCreateView.as_view(), name='create'),
    path('<int:pk>/', views.LeadDetailView.as_view(), name='detail'),
    path('<int:pk>/update/', views.LeadUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.LeadDeleteView.as_view(), name='delete'),
    
    # Lead Activity URLs
    path('<int:pk>/activity/add/', views.add_activity, name='add_activity'),
    path('<int:pk>/activities/', views.lead_activity_list, name='activity_list'),
    
    # Bulk Operations
    path('bulk-update/', views.bulk_update_leads, name='bulk_update'),
    
    # Export and API URLs
    path('export/', views.export_leads, name='export'),
    path('api/stats/', views.lead_stats_api, name='stats_api'),
]