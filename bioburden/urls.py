from django.urls import path
from . import views

app_name = 'bioburden'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Data management
    path('data/', views.BioburdenDataListView.as_view(), name='data_list'),
    path('data/add/', views.BioburdenDataCreateView.as_view(), name='data_create'),
    path('data/<int:pk>/edit/', views.BioburdenDataUpdateView.as_view(), name='data_update'),
    
    # Thresholds
    path('thresholds/', views.FixedThresholdListView.as_view(), name='threshold_list'),
    path('thresholds/add/', views.FixedThresholdCreateView.as_view(), name='threshold_create'),
    path('thresholds/<int:pk>/edit/', views.FixedThresholdUpdateView.as_view(), name='threshold_update'),
    
    # Import
    path('import/', views.import_data, name='import_data'),
    path('import/<int:pk>/', views.import_detail, name='import_detail'),
    
    # Analysis
    path('lot/<int:pk>/', views.lot_detail, name='lot_detail'),
    path('area-comparison/', views.area_comparison, name='area_comparison'),
    path('outlier-analysis/', views.outlier_analysis, name='outlier_analysis'),
    path('organism-frequency/', views.organism_frequency, name='organism_frequency'),
    path('cfu-per-area/', views.cfu_per_area_analysis, name='cfu_per_area_analysis'),
    path('statistical-summary/', views.statistical_summary, name='statistical_summary'),
    
    # API
    path('api/chart-data/', views.chart_data_api, name='chart_data_api'),
]
