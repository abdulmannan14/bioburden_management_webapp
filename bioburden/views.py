from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Avg, Count, Max, Min, StdDev, Q
from django.http import JsonResponse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import (
    BioburdenData, Area, Lot, FixedThreshold, 
    DynamicThreshold, DataImport
)
from .forms import (
    DataImportForm, BioburdenDataForm, 
    FixedThresholdForm, FilterForm
)
from .utils import ExcelImporter


def dashboard(request):
    """Main dashboard view with charts and metrics"""
    
    # Apply filters
    filter_form = FilterForm(request.GET)
    queryset = BioburdenData.objects.all()
    
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('lot'):
            queryset = queryset.filter(lot=filter_form.cleaned_data['lot'])
        if filter_form.cleaned_data.get('area'):
            queryset = queryset.filter(area=filter_form.cleaned_data['area'])
        if filter_form.cleaned_data.get('date_from'):
            queryset = queryset.filter(test_date__gte=filter_form.cleaned_data['date_from'])
        if filter_form.cleaned_data.get('date_to'):
            queryset = queryset.filter(test_date__lte=filter_form.cleaned_data['date_to'])
        if filter_form.cleaned_data.get('status'):
            queryset = queryset.filter(status=filter_form.cleaned_data['status'])
    
    # Statistics
    total_tests = queryset.count()
    alert_count = queryset.filter(status='alert').count()
    action_count = queryset.filter(status='action').count()
    
    # Recent tests
    recent_tests = queryset.select_related('lot', 'area').order_by('-test_date')[:10]
    
    # Status distribution
    status_distribution = queryset.values('status').annotate(count=Count('id'))
    
    # Area comparison
    area_stats = queryset.values('area__name').annotate(
        avg_cfu=Avg('adjusted_cfu'),
        max_cfu=Max('adjusted_cfu'),
        count=Count('id')
    ).order_by('-avg_cfu')
    
    # Lot comparison
    lot_stats = queryset.values('lot__lot_number').annotate(
        avg_cfu=Avg('adjusted_cfu'),
        max_cfu=Max('adjusted_cfu'),
        alert_count=Count('id', filter=Q(status='alert')),
        action_count=Count('id', filter=Q(status='action')),
    ).order_by('-action_count', '-alert_count')[:10]
    
    context = {
        'filter_form': filter_form,
        'total_tests': total_tests,
        'alert_count': alert_count,
        'action_count': action_count,
        'normal_count': total_tests - alert_count - action_count,
        'recent_tests': recent_tests,
        'status_distribution': list(status_distribution),
        'area_stats': list(area_stats),
        'lot_stats': list(lot_stats),
    }
    
    return render(request, 'bioburden/dashboard.html', context)


def chart_data_api(request):
    """API endpoint for chart data (AJAX)"""
    
    lot_id = request.GET.get('lot')
    area_id = request.GET.get('area')
    
    queryset = BioburdenData.objects.all()
    
    if lot_id:
        queryset = queryset.filter(lot_id=lot_id)
    if area_id:
        queryset = queryset.filter(area_id=area_id)
    
    # Time series data
    data = queryset.select_related('lot', 'area').order_by('test_date').values(
        'test_date', 'adjusted_cfu', 'cfu_count', 'status', 
        'lot__lot_number', 'area__name'
    )
    
    # Get thresholds
    thresholds = {}
    if lot_id:
        try:
            lot = Lot.objects.get(id=lot_id)
            if hasattr(lot, 'threshold'):
                thresholds = {
                    'alert_level': float(lot.threshold.alert_level),
                    'action_level': float(lot.threshold.action_level)
                }
        except Lot.DoesNotExist:
            pass
    
    # Convert to list and format dates
    chart_data = []
    for item in data:
        chart_data.append({
            'date': item['test_date'].strftime('%Y-%m-%d'),
            'value': float(item['adjusted_cfu'] or item['cfu_count']),
            'status': item['status'],
            'lot': item['lot__lot_number'],
            'area': item['area__name']
        })
    
    return JsonResponse({
        'data': chart_data,
        'thresholds': thresholds
    })


def import_data(request):
    """Import bioburden data from Excel"""
    
    if request.method == 'POST':
        form = DataImportForm(request.POST, request.FILES)
        if form.is_valid():
            data_import = form.save(commit=False)
            data_import.status = 'processing'
            data_import.file_name = request.FILES['uploaded_file'].name
            data_import.save()
            
            try:
                # Import data using the utility
                importer = ExcelImporter(data_import.uploaded_file.path)
                result = importer.detect_and_import()
                
                # Update import record
                data_import.records_imported = result['records_imported']
                data_import.status = 'completed' if result['success'] else 'failed'
                data_import.error_message = '\n'.join(result['errors'] + result['warnings'])
                data_import.save()
                
                if result['success']:
                    messages.success(request, f"Successfully imported {result['records_imported']} records!")
                    if result['warnings']:
                        messages.warning(request, f"Warnings: {len(result['warnings'])} issues found.")
                else:
                    messages.error(request, "Import failed. Check errors below.")
                
                return redirect('bioburden:import_detail', pk=data_import.pk)
                
            except Exception as e:
                data_import.status = 'failed'
                data_import.error_message = str(e)
                data_import.save()
                messages.error(request, f"Import failed: {str(e)}")
    else:
        form = DataImportForm()
    
    # Recent imports
    recent_imports = DataImport.objects.order_by('-upload_date')[:10]
    
    context = {
        'form': form,
        'recent_imports': recent_imports
    }
    
    return render(request, 'bioburden/import_data.html', context)


def import_detail(request, pk):
    """View details of a data import"""
    data_import = get_object_or_404(DataImport, pk=pk)
    
    context = {
        'data_import': data_import,
        'errors': data_import.error_message.split('\n') if data_import.error_message else []
    }
    
    return render(request, 'bioburden/import_detail.html', context)


class BioburdenDataListView(ListView):
    """List all bioburden test data"""
    model = BioburdenData
    template_name = 'bioburden/data_list.html'
    context_object_name = 'tests'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('lot', 'area')
        
        # Apply filters
        lot_id = self.request.GET.get('lot')
        area_id = self.request.GET.get('area')
        status = self.request.GET.get('status')
        
        if lot_id:
            queryset = queryset.filter(lot_id=lot_id)
        if area_id:
            queryset = queryset.filter(area_id=area_id)
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-test_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = FilterForm(self.request.GET)
        return context


class BioburdenDataCreateView(CreateView):
    """Create new bioburden test record"""
    model = BioburdenData
    form_class = BioburdenDataForm
    template_name = 'bioburden/data_form.html'
    success_url = reverse_lazy('bioburden:data_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Bioburden test record created successfully!")
        return super().form_valid(form)


class BioburdenDataUpdateView(UpdateView):
    """Update bioburden test record"""
    model = BioburdenData
    form_class = BioburdenDataForm
    template_name = 'bioburden/data_form.html'
    success_url = reverse_lazy('bioburden:data_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Bioburden test record updated successfully!")
        return super().form_valid(form)


class FixedThresholdListView(ListView):
    """List all fixed thresholds"""
    model = FixedThreshold
    template_name = 'bioburden/threshold_list.html'
    context_object_name = 'thresholds'
    paginate_by = 50
    
    def get_queryset(self):
        return super().get_queryset().select_related('lot', 'area')


class FixedThresholdCreateView(CreateView):
    """Create new fixed threshold"""
    model = FixedThreshold
    form_class = FixedThresholdForm
    template_name = 'bioburden/threshold_form.html'
    success_url = reverse_lazy('bioburden:threshold_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Fixed threshold created successfully!")
        return super().form_valid(form)


class FixedThresholdUpdateView(UpdateView):
    """Update fixed threshold"""
    model = FixedThreshold
    form_class = FixedThresholdForm
    template_name = 'bioburden/threshold_form.html'
    success_url = reverse_lazy('bioburden:threshold_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Fixed threshold updated successfully!")
        return super().form_valid(form)


def lot_detail(request, pk):
    """Detailed view for a specific lot"""
    lot = get_object_or_404(Lot, pk=pk)
    
    # Get all tests for this lot
    tests = BioburdenData.objects.filter(lot=lot).select_related('area').order_by('-test_date')
    
    # Statistics
    stats = tests.aggregate(
        avg_cfu=Avg('adjusted_cfu'),
        max_cfu=Max('adjusted_cfu'),
        min_cfu=Min('adjusted_cfu'),
        std_dev=StdDev('adjusted_cfu'),
        total_tests=Count('id'),
        alert_count=Count('id', filter=Q(status='alert')),
        action_count=Count('id', filter=Q(status='action'))
    )
    
    # Get threshold
    threshold = None
    if hasattr(lot, 'threshold'):
        threshold = lot.threshold
    
    # Area breakdown
    area_breakdown = tests.values('area__name', 'status').annotate(
        count=Count('id'),
        avg_cfu=Avg('adjusted_cfu')
    )
    
    context = {
        'lot': lot,
        'tests': tests,
        'stats': stats,
        'threshold': threshold,
        'area_breakdown': area_breakdown
    }
    
    return render(request, 'bioburden/lot_detail.html', context)


def area_comparison(request):
    """Compare bioburden levels across different areas"""
    
    areas = Area.objects.all()
    
    area_data = []
    for area in areas:
        tests = BioburdenData.objects.filter(area=area)
        stats = tests.aggregate(
            avg_cfu=Avg('adjusted_cfu'),
            max_cfu=Max('adjusted_cfu'),
            total_tests=Count('id'),
            alert_count=Count('id', filter=Q(status='alert')),
            action_count=Count('id', filter=Q(status='action'))
        )
        
        area_data.append({
            'area': area,
            'stats': stats
        })
    
    context = {
        'area_data': area_data
    }
    
    return render(request, 'bioburden/area_comparison.html', context)


def outlier_analysis(request):
    """Statistical outlier detection for lots"""
    import numpy as np
    from scipy import stats as scipy_stats
    
    lots = Lot.objects.all()
    outlier_data = []
    
    for lot in lots:
        tests = BioburdenData.objects.filter(lot=lot)
        
        if tests.count() == 0:
            continue
        
        # Get CFU values
        cfu_values = [float(test.adjusted_cfu or test.cfu_count) for test in tests]
        
        if len(cfu_values) < 3:
            continue
        
        # Calculate statistics
        mean_cfu = np.mean(cfu_values)
        std_cfu = np.std(cfu_values)
        median_cfu = np.median(cfu_values)
        
        # Calculate Z-scores
        z_scores = scipy_stats.zscore(cfu_values) if std_cfu > 0 else [0] * len(cfu_values)
        
        # Identify outliers (|Z| > 2 is common threshold)
        outlier_count = sum(1 for z in z_scores if abs(z) > 2)
        outlier_percentage = (outlier_count / len(cfu_values)) * 100 if len(cfu_values) > 0 else 0
        
        # Determine status
        if outlier_percentage == 0:
            status = 'CLEAN: No outliers'
            status_class = 'success'
        elif outlier_percentage < 10:
            status = f'GOOD: <10% outliers'
            status_class = 'info'
        else:
            status = f'WARNING: ≥10% outliers'
            status_class = 'warning'
        
        outlier_data.append({
            'lot': lot,
            'mean_cfu': round(mean_cfu, 2),
            'std_cfu': round(std_cfu, 2),
            'median_cfu': round(median_cfu, 2),
            'total_samples': len(cfu_values),
            'outlier_count': outlier_count,
            'outlier_percentage': round(outlier_percentage, 1),
            'status': status,
            'status_class': status_class
        })
    
    # Sort by outlier percentage descending
    outlier_data.sort(key=lambda x: x['outlier_percentage'], reverse=True)
    
    context = {
        'outlier_data': outlier_data
    }
    
    return render(request, 'bioburden/outlier_analysis.html', context)


def organism_frequency(request):
    """Organism frequency analysis by lot and organism type"""
    
    # Organism frequency by lot
    lots_with_organisms = Lot.objects.exclude(primary_organism__isnull=True)
    
    lot_organism_data = []
    for lot in lots_with_organisms:
        organisms = []
        if lot.primary_organism:
            organisms.append(('Primary', lot.primary_organism))
        if lot.secondary_organism:
            organisms.append(('Secondary', lot.secondary_organism))
        if lot.tertiary_organism:
            organisms.append(('Tertiary', lot.tertiary_organism))
        
        organism_count = len(organisms)
        
        lot_organism_data.append({
            'lot': lot,
            'organism_count': organism_count,
            'organisms': organisms,
            'production_date': lot.production_date
        })
    
    # Organism frequency summary
    from collections import Counter
    
    all_organisms = []
    for lot in lots_with_organisms:
        if lot.primary_organism:
            all_organisms.append(lot.primary_organism)
        if lot.secondary_organism:
            all_organisms.append(lot.secondary_organism)
        if lot.tertiary_organism:
            all_organisms.append(lot.tertiary_organism)
    
    organism_counts = Counter(all_organisms)
    organism_summary = [
        {'name': org, 'count': count, 'percentage': round((count/len(all_organisms))*100, 1)}
        for org, count in organism_counts.most_common()
    ]
    
    context = {
        'lot_organism_data': lot_organism_data,
        'organism_summary': organism_summary,
        'total_organisms': len(all_organisms),
        'unique_organisms': len(organism_counts)
    }
    
    return render(request, 'bioburden/organism_frequency.html', context)


def cfu_per_area_analysis(request):
    """Detailed CFU analysis per area with statistics"""
    
    areas = Area.objects.all()
    area_analysis = []
    
    for area in areas:
        tests = BioburdenData.objects.filter(area=area)
        
        if tests.count() == 0:
            continue
        
        # Get CFU values
        cfu_values = [float(test.adjusted_cfu or test.cfu_count) for test in tests]
        
        if len(cfu_values) > 0:
            import numpy as np
            
            stats_data = {
                'area': area,
                'total_tests': len(cfu_values),
                'mean_cfu': round(np.mean(cfu_values), 2),
                'median_cfu': round(np.median(cfu_values), 2),
                'std_cfu': round(np.std(cfu_values), 2),
                'min_cfu': round(min(cfu_values), 2),
                'max_cfu': round(max(cfu_values), 2),
                'range_cfu': round(max(cfu_values) - min(cfu_values), 2),
            }
            
            # Calculate percentiles
            stats_data['percentile_25'] = round(np.percentile(cfu_values, 25), 2)
            stats_data['percentile_75'] = round(np.percentile(cfu_values, 75), 2)
            
            # Status counts
            stats_data['normal_count'] = tests.filter(status='normal').count()
            stats_data['alert_count'] = tests.filter(status='alert').count()
            stats_data['action_count'] = tests.filter(status='action').count()
            
            area_analysis.append(stats_data)
    
    # Sort by mean CFU descending
    area_analysis.sort(key=lambda x: x['mean_cfu'], reverse=True)
    
    context = {
        'area_analysis': area_analysis
    }
    
    return render(request, 'bioburden/cfu_per_area_analysis.html', context)


def statistical_summary(request):
    """Comprehensive statistical summary and Z-score analysis"""
    import numpy as np
    from scipy import stats as scipy_stats
    
    # Overall statistics
    all_tests = BioburdenData.objects.all()
    cfu_values = [float(test.adjusted_cfu or test.cfu_count) for test in all_tests]
    
    if len(cfu_values) > 0:
        overall_stats = {
            'total_tests': len(cfu_values),
            'mean': round(np.mean(cfu_values), 2),
            'median': round(np.median(cfu_values), 2),
            'std': round(np.std(cfu_values), 2),
            'variance': round(np.var(cfu_values), 2),
            'min': round(min(cfu_values), 2),
            'max': round(max(cfu_values), 2),
            'range': round(max(cfu_values) - min(cfu_values), 2),
            'cv': round((np.std(cfu_values) / np.mean(cfu_values)) * 100, 2) if np.mean(cfu_values) > 0 else 0
        }
        
        # Calculate Z-scores for recent tests
        z_scores = scipy_stats.zscore(cfu_values) if overall_stats['std'] > 0 else [0] * len(cfu_values)
        
        # Get tests with high Z-scores (outliers)
        recent_tests = list(all_tests.order_by('-test_date')[:20])
        recent_with_z = []
        
        for i, test in enumerate(all_tests.order_by('-test_date')[:20]):
            idx = list(all_tests.order_by('-test_date')[:20]).index(test)
            if idx < len(z_scores):
                z_score = z_scores[-(idx+1)]  # Reverse index
                recent_with_z.append({
                    'test': test,
                    'z_score': round(z_score, 2),
                    'abs_z_score': round(abs(z_score), 2),
                    'is_outlier': abs(z_score) > 2
                })
    else:
        overall_stats = None
        recent_with_z = []
    
    # Threshold comparison
    thresholds = FixedThreshold.objects.first()
    
    context = {
        'overall_stats': overall_stats,
        'recent_with_z': recent_with_z,
        'thresholds': thresholds
    }
    
    return render(request, 'bioburden/statistical_summary.html', context)
