import openpyxl
import pandas as pd
from datetime import datetime
from decimal import Decimal
from django.utils import timezone
from .models import Area, Lot, BioburdenData, FixedThreshold, DataImport


class ExcelImporter:
    """Handle Excel file imports for bioburden data"""
    
    def __init__(self, file_path):
        self.file_path = file_path
        self.errors = []
        self.warnings = []
        self.records_imported = 0
    
    def import_bioburden_data(self, sheet_name='Bioburden Data'):
        """Import bioburden data from Excel sheet"""
        try:
            # Read Excel file
            df = pd.read_excel(self.file_path, sheet_name=sheet_name)
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            for index, row in df.iterrows():
                try:
                    # Skip empty rows
                    if pd.isna(row.get('Lot')) or pd.isna(row.get('Area')):
                        continue
                    
                    # Get or create lot
                    lot_number = str(row.get('Lot', '')).strip()
                    lot, created = Lot.objects.get_or_create(
                        lot_number=lot_number,
                        defaults={
                            'product_name': row.get('Product', ''),
                        }
                    )
                    
                    # Get or create area
                    area_name = str(row.get('Area', '')).strip()
                    area, created = Area.objects.get_or_create(
                        name=area_name
                    )
                    
                    # Parse test date
                    test_date = row.get('Test Date') or row.get('Date')
                    if pd.isna(test_date):
                        test_date = timezone.now().date()
                    elif isinstance(test_date, str):
                        test_date = pd.to_datetime(test_date).date()
                    else:
                        test_date = test_date.date() if hasattr(test_date, 'date') else test_date
                    
                    # Get CFU count
                    cfu_count = row.get('CFU') or row.get('CFU Count') or row.get('Count')
                    if pd.isna(cfu_count):
                        cfu_count = 0
                    cfu_count = Decimal(str(cfu_count))
                    
                    # Get dilution factor
                    dilution_factor = row.get('Dilution') or row.get('Dilution Factor')
                    if pd.isna(dilution_factor):
                        dilution_factor = 1.0
                    dilution_factor = Decimal(str(dilution_factor))
                    
                    # Create bioburden data record
                    BioburdenData.objects.create(
                        lot=lot,
                        area=area,
                        test_date=test_date,
                        sample_id=row.get('Sample ID', ''),
                        cfu_count=cfu_count,
                        dilution_factor=dilution_factor,
                        lab_name=row.get('Laboratory', ''),
                        analyst=row.get('Analyst', ''),
                        notes=row.get('Notes', '')
                    )
                    
                    self.records_imported += 1
                    
                except Exception as e:
                    self.errors.append(f"Row {index + 2}: {str(e)}")
            
            return True
            
        except Exception as e:
            self.errors.append(f"Failed to import bioburden data: {str(e)}")
            return False
    
    def import_fixed_thresholds(self, sheet_name='Thresholds'):
        """Import fixed alert and action levels from Excel"""
        try:
            df = pd.read_excel(self.file_path, sheet_name=sheet_name)
            df.columns = df.columns.str.strip()
            
            for index, row in df.iterrows():
                try:
                    # Skip empty rows
                    if pd.isna(row.get('Lot')):
                        continue
                    
                    # Get lot
                    lot_number = str(row.get('Lot', '')).strip()
                    lot, created = Lot.objects.get_or_create(lot_number=lot_number)
                    
                    # Get area if specified
                    area = None
                    area_name = row.get('Area')
                    if area_name and not pd.isna(area_name):
                        area, _ = Area.objects.get_or_create(name=str(area_name).strip())
                    
                    # Get alert and action levels
                    alert_level = row.get('Alert Level') or row.get('Alert')
                    action_level = row.get('Action Level') or row.get('Action')
                    
                    if pd.isna(alert_level) or pd.isna(action_level):
                        self.warnings.append(f"Row {index + 2}: Missing alert or action level for lot {lot_number}")
                        continue
                    
                    alert_level = Decimal(str(alert_level))
                    action_level = Decimal(str(action_level))
                    
                    # Create or update threshold
                    FixedThreshold.objects.update_or_create(
                        lot=lot,
                        defaults={
                            'area': area,
                            'alert_level': alert_level,
                            'action_level': action_level,
                            'notes': row.get('Notes', '')
                        }
                    )
                    
                except Exception as e:
                    self.errors.append(f"Threshold row {index + 2}: {str(e)}")
            
            return True
            
        except Exception as e:
            self.warnings.append(f"No thresholds sheet found or error: {str(e)}")
            return False
    
    def detect_and_import(self):
        """Automatically detect sheets and import data"""
        workbook = openpyxl.load_workbook(self.file_path, read_only=True)
        sheet_names = workbook.sheetnames
        
        # Try to find bioburden data sheet
        bioburden_sheets = [s for s in sheet_names if 'bioburden' in s.lower() or 'data' in s.lower()]
        if bioburden_sheets:
            self.import_bioburden_data(bioburden_sheets[0])
        else:
            self.import_bioburden_data(sheet_names[0])  # Use first sheet
        
        # Try to find threshold sheet
        threshold_sheets = [s for s in sheet_names if 'threshold' in s.lower() or 'alert' in s.lower() or 'action' in s.lower()]
        if threshold_sheets:
            self.import_fixed_thresholds(threshold_sheets[0])
        
        return {
            'success': len(self.errors) == 0,
            'records_imported': self.records_imported,
            'errors': self.errors,
            'warnings': self.warnings
        }
