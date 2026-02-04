from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal


class Area(models.Model):
    """Areas where bioburden testing is performed"""
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Lot(models.Model):
    """Product lots being tested"""
    lot_number = models.CharField(max_length=100, unique=True)
    product_name = models.CharField(max_length=200, blank=True, null=True)
    manufacture_date = models.DateField(blank=True, null=True)
    production_date = models.DateField(blank=True, null=True)
    primary_organism = models.CharField(max_length=200, blank=True, null=True)
    secondary_organism = models.CharField(max_length=200, blank=True, null=True)
    tertiary_organism = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-lot_number']
    
    def __str__(self):
        return self.lot_number


class FixedThreshold(models.Model):
    """Fixed alert and action levels by lot (reference table)"""
    lot = models.OneToOneField(Lot, on_delete=models.CASCADE, related_name='threshold')
    area = models.ForeignKey(Area, on_delete=models.CASCADE, blank=True, null=True)
    alert_level = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Orange alert threshold"
    )
    action_level = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Red action threshold"
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['lot__lot_number']
        verbose_name = 'Fixed Threshold'
        verbose_name_plural = 'Fixed Thresholds'
    
    def __str__(self):
        return f"{self.lot.lot_number} - Alert: {self.alert_level}, Action: {self.action_level}"


class BioburdenData(models.Model):
    """Main bioburden test data from laboratory"""
    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, related_name='bioburden_tests')
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='bioburden_tests')
    test_date = models.DateField()
    sample_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Bioburden measurements (CFU - Colony Forming Units)
    cfu_count = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Colony Forming Units count"
    )
    
    # Dilution factor if applicable
    dilution_factor = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=1.0,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Calculated adjusted CFU
    adjusted_cfu = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        blank=True,
        null=True,
        help_text="CFU adjusted for dilution"
    )
    
    # Laboratory information
    lab_name = models.CharField(max_length=200, blank=True, null=True)
    analyst = models.CharField(max_length=100, blank=True, null=True)
    
    # Additional notes
    notes = models.TextField(blank=True, null=True)
    
    # Status tracking
    STATUS_CHOICES = [
        ('normal', 'Normal'),
        ('alert', 'Alert Level Exceeded'),
        ('action', 'Action Level Exceeded'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='normal')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-test_date', 'lot__lot_number']
        verbose_name = 'Bioburden Test'
        verbose_name_plural = 'Bioburden Tests'
        indexes = [
            models.Index(fields=['lot', 'test_date']),
            models.Index(fields=['area', 'test_date']),
            models.Index(fields=['status']),
        ]
    
    def save(self, *args, **kwargs):
        # Calculate adjusted CFU
        if self.cfu_count and self.dilution_factor:
            self.adjusted_cfu = self.cfu_count * self.dilution_factor
        
        # Determine status based on fixed thresholds
        if hasattr(self.lot, 'threshold'):
            threshold = self.lot.threshold
            value = self.adjusted_cfu or self.cfu_count
            
            if value >= threshold.action_level:
                self.status = 'action'
            elif value >= threshold.alert_level:
                self.status = 'alert'
            else:
                self.status = 'normal'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.lot.lot_number} - {self.area.name} ({self.test_date})"
    
    @property
    def get_value(self):
        """Get the value to compare against thresholds"""
        return self.adjusted_cfu or self.cfu_count
    
    def get_status_color(self):
        """Return color code for status"""
        colors = {
            'normal': '#28a745',  # Green
            'alert': '#fd7e14',   # Orange
            'action': '#dc3545',  # Red
        }
        return colors.get(self.status, '#6c757d')


class DynamicThreshold(models.Model):
    """Dynamic alert and action levels calculated from historical data"""
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='dynamic_thresholds')
    calculation_date = models.DateField(default=timezone.now)
    
    # Statistical values
    mean_value = models.DecimalField(max_digits=10, decimal_places=2)
    std_deviation = models.DecimalField(max_digits=10, decimal_places=2)
    sample_count = models.IntegerField()
    
    # Calculated thresholds
    dynamic_alert_level = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Calculated as mean + 2*std"
    )
    dynamic_action_level = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Calculated as mean + 3*std"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-calculation_date', 'area']
        verbose_name = 'Dynamic Threshold'
        verbose_name_plural = 'Dynamic Thresholds'
    
    def __str__(self):
        return f"{self.area.name} - Dynamic ({self.calculation_date})"


class DataImport(models.Model):
    """Track Excel file imports"""
    file_name = models.CharField(max_length=255)
    uploaded_file = models.FileField(upload_to='imports/')
    upload_date = models.DateTimeField(auto_now_add=True)
    records_imported = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='pending')
    error_message = models.TextField(blank=True, null=True)
    imported_by = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        ordering = ['-upload_date']
    
    def __str__(self):
        return f"{self.file_name} - {self.upload_date.strftime('%Y-%m-%d %H:%M')}"
