from django.contrib import admin
from .models import Area, Lot, BioburdenData, FixedThreshold, DynamicThreshold, DataImport


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name', 'description']


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ['lot_number', 'product_name', 'manufacture_date', 'created_at']
    search_fields = ['lot_number', 'product_name']
    list_filter = ['manufacture_date']


@admin.register(FixedThreshold)
class FixedThresholdAdmin(admin.ModelAdmin):
    list_display = ['lot', 'area', 'alert_level', 'action_level', 'updated_at']
    list_filter = ['area']
    search_fields = ['lot__lot_number']
    raw_id_fields = ['lot', 'area']


@admin.register(BioburdenData)
class BioburdenDataAdmin(admin.ModelAdmin):
    list_display = ['lot', 'area', 'test_date', 'cfu_count', 'adjusted_cfu', 'status', 'get_status_badge']
    list_filter = ['status', 'area', 'test_date', 'lot']
    search_fields = ['lot__lot_number', 'area__name', 'sample_id']
    date_hierarchy = 'test_date'
    raw_id_fields = ['lot', 'area']
    readonly_fields = ['adjusted_cfu', 'status', 'created_at', 'updated_at']
    
    def get_status_badge(self, obj):
        colors = {
            'normal': 'green',
            'alert': 'orange',
            'action': 'red',
        }
        return f'<span style="background-color: {colors.get(obj.status, "gray")}; color: white; padding: 3px 8px; border-radius: 3px;">{obj.get_status_display()}</span>'
    get_status_badge.short_description = 'Status Badge'
    get_status_badge.allow_tags = True


@admin.register(DynamicThreshold)
class DynamicThresholdAdmin(admin.ModelAdmin):
    list_display = ['area', 'calculation_date', 'mean_value', 'std_deviation', 'dynamic_alert_level', 'dynamic_action_level']
    list_filter = ['area', 'calculation_date']
    readonly_fields = ['created_at']


@admin.register(DataImport)
class DataImportAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'upload_date', 'records_imported', 'status', 'imported_by']
    list_filter = ['status', 'upload_date']
    search_fields = ['file_name', 'imported_by']
    readonly_fields = ['upload_date']
