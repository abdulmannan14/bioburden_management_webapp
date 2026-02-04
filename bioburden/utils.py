import openpyxl
import pandas as pd
from datetime import datetime
from decimal import Decimal
from django.utils import timezone
from .models import Area, Lot, BioburdenData, FixedThreshold, DataImport


class ExcelImporter:
    """Handle Excel file imports for bioburden data - matches import_complete_data.py logic"""
    
    def __init__(self, file_path):
        self.file_path = file_path
        self.errors = []
        self.warnings = []
        self.records_imported = 0
        self.clear_existing_data = True  # Default behavior
    
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
    
    def import_lot_master(self):
        """Import lot details with organism identification from LOT_MASTER sheet"""
        try:
            df = pd.read_excel(self.file_path, sheet_name='LOT_MASTER')
            df.columns = df.columns.str.strip()
            
            lots_created = 0
            for index, row in df.iterrows():
                try:
                    lot_number = str(row.get('LOT VECTOR', '')).strip()
                    if not lot_number or pd.isna(lot_number):
                        continue
                    
                    # Parse production date
                    prod_date = row.get('DATE PRODUCTION')
                    if pd.notna(prod_date):
                        if isinstance(prod_date, str):
                            prod_date = pd.to_datetime(prod_date).date()
                        else:
                            prod_date = prod_date.date() if hasattr(prod_date, 'date') else prod_date
                    else:
                        prod_date = None
                    
                    # Get organisms
                    primary_org = row.get('PRIMARY_ORGANISM')
                    secondary_org = row.get('SECONDARY_ORGANISM')
                    tertiary_org = row.get('TERTIARY_ORGANISM')
                    
                    # Create or update lot
                    Lot.objects.update_or_create(
                        lot_number=lot_number,
                        defaults={
                            'production_date': prod_date,
                            'primary_organism': primary_org if pd.notna(primary_org) else None,
                            'secondary_organism': secondary_org if pd.notna(secondary_org) else None,
                            'tertiary_organism': tertiary_org if pd.notna(tertiary_org) else None,
                        }
                    )
                    lots_created += 1
                    
                except Exception as e:
                    self.errors.append(f"LOT_MASTER row {index + 2}: {str(e)}")
            
            if lots_created > 0:
                self.warnings.append(f"✓ Imported {lots_created} lots with organism data")
            return True
            
        except Exception as e:
            self.warnings.append(f"LOT_MASTER sheet not found or error: {str(e)}")
            return False
    
    def import_raw_data(self):
        """Import bioburden test data from RAW DATA sheet"""
        try:
            df = pd.read_excel(self.file_path, sheet_name='RAW DATA')
            df.columns = df.columns.str.strip()
            
            for index, row in df.iterrows():
                try:
                    # Get lot and area
                    lot_number = str(row.get('LOT VECTOR', '')).strip()
                    area_name = str(row.get('AREA TESTED', '')).strip()
                    
                    if not lot_number or not area_name or pd.isna(lot_number) or pd.isna(area_name):
                        continue
                    
                    # Get or create lot and area
                    lot, _ = Lot.objects.get_or_create(lot_number=lot_number)
                    area, _ = Area.objects.get_or_create(name=area_name)
                    
                    # Parse test date
                    test_date = row.get('DATE')
                    if pd.isna(test_date):
                        test_date = timezone.now().date()
                    elif isinstance(test_date, str):
                        test_date = pd.to_datetime(test_date).date()
                    else:
                        test_date = test_date.date() if hasattr(test_date, 'date') else test_date
                    
                    # Get correction factor
                    correction_factor = row.get('CORRECTION FACTOR', 1.0)
                    if pd.isna(correction_factor):
                        correction_factor = 1.0
                    correction_factor = float(correction_factor)
                    
                    # Import AEROBES
                    aerobe_cols = [c for c in df.columns if 'CFU AEROBES' in c and c.startswith('CFU AEROBES S')]
                    for col in aerobe_cols:
                        cfu_value = row.get(col)
                        if pd.notna(cfu_value):
                            sample_num = col.replace('CFU AEROBES S', '').strip()
                            BioburdenData.objects.create(
                                lot=lot,
                                area=area,
                                test_date=test_date,
                                sample_id=f"AEROBES-S{sample_num}",
                                cfu_count=Decimal(str(cfu_value)),
                                adjusted_cfu=Decimal(str(float(cfu_value) * correction_factor)),
                                dilution_factor=Decimal(str(correction_factor)),
                                lab_name=row.get('PROVIDER', ''),
                            )
                            self.records_imported += 1
                    
                    # Import FUNGI
                    fungi_cols = [c for c in df.columns if 'CFU FUNGI' in c and c.startswith('CFU FUNGI S')]
                    for col in fungi_cols:
                        cfu_value = row.get(col)
                        if pd.notna(cfu_value):
                            sample_num = col.replace('CFU FUNGI S', '').strip()
                            BioburdenData.objects.create(
                                lot=lot,
                                area=area,
                                test_date=test_date,
                                sample_id=f"FUNGI-S{sample_num}",
                                cfu_count=Decimal(str(cfu_value)),
                                adjusted_cfu=Decimal(str(float(cfu_value) * correction_factor)),
                                dilution_factor=Decimal(str(correction_factor)),
                                lab_name=row.get('PROVIDER', ''),
                            )
                            self.records_imported += 1
                    
                except Exception as e:
                    self.errors.append(f"RAW DATA row {index + 2}: {str(e)}")
            
            if self.records_imported > 0:
                self.warnings.append(f"✓ Imported {self.records_imported} bioburden test records")
            return True
            
        except Exception as e:
            self.errors.append(f"Failed to import RAW DATA: {str(e)}")
            return False
    
    def import_alert_action_levels(self):
        """Import fixed thresholds from ALERT_ACTION LEVELS sheet"""
        try:
            df = pd.read_excel(self.file_path, sheet_name='ALERT_ACTION LEVELS')
            df.columns = df.columns.str.strip()
            
            # Get the most recent (last row) threshold values
            if len(df) > 0:
                last_row = df.iloc[-1]
                alert_level = Decimal(str(last_row.get('ALERT LEVEL FIXED', 0)))
                action_level = Decimal(str(last_row.get('ACTION LEVEL FIXED', 0)))
                
                # Create thresholds for all lots
                lots = Lot.objects.all()
                thresholds_created = 0
                for lot in lots:
                    FixedThreshold.objects.update_or_create(
                        lot=lot,
                        defaults={
                            'alert_level': alert_level,
                            'action_level': action_level,
                        }
                    )
                    thresholds_created += 1
                
                self.warnings.append(f"✓ Created {thresholds_created} fixed thresholds (Alert: {alert_level}, Action: {action_level})")
                return True
            else:
                self.warnings.append("ALERT_ACTION LEVELS sheet is empty")
                return False
                
        except Exception as e:
            self.warnings.append(f"ALERT_ACTION LEVELS sheet not found or error: {str(e)}")
            return False
    
    def detect_and_import(self):
        """Automatically detect sheets and import complete data"""
        try:
            workbook = openpyxl.load_workbook(self.file_path, read_only=True)
            sheet_names = workbook.sheetnames
            workbook.close()
            
            # Clear existing data if requested
            if self.clear_existing_data:
                BioburdenData.objects.all().delete()
                FixedThreshold.objects.all().delete()
                Lot.objects.all().delete()
                Area.objects.all().delete()
                self.warnings.append("✓ Cleared existing data")
            
            # Import in proper order
            # 1. LOT_MASTER (creates lots with organism data)
            if 'LOT_MASTER' in sheet_names:
                self.import_lot_master()
            
            # 2. RAW DATA (creates bioburden tests)
            if 'RAW DATA' in sheet_names:
                self.import_raw_data()
            else:
                # Fallback to old method if RAW DATA sheet doesn't exist
                bioburden_sheets = [s for s in sheet_names if 'bioburden' in s.lower() or 'data' in s.lower()]
                if bioburden_sheets:
                    self.import_bioburden_data(bioburden_sheets[0])
                else:
                    self.import_bioburden_data(sheet_names[0])
            
            # 3. ALERT_ACTION LEVELS (creates thresholds)
            if 'ALERT_ACTION LEVELS' in sheet_names:
                self.import_alert_action_levels()
            else:
                # Fallback to old method
                threshold_sheets = [s for s in sheet_names if 'threshold' in s.lower() or 'alert' in s.lower()]
                if threshold_sheets:
                    self.import_fixed_thresholds(threshold_sheets[0])
            
            # Recalculate status for all tests
            for test in BioburdenData.objects.all():
                test.save()  # This triggers status calculation
            
            return {
                'success': len(self.errors) == 0,
                'records_imported': self.records_imported,
                'errors': self.errors,
                'warnings': self.warnings
            }
            
        except Exception as e:
            self.errors.append(f"Fatal error during import: {str(e)}")
            return {
                'success': False,
                'records_imported': self.records_imported,
                'errors': self.errors,
                'warnings': self.warnings
            }

