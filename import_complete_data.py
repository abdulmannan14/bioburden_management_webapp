"""
COMPLETE import of ALL relevant data from Excel file
Includes: RAW DATA, LOT_MASTER, ALERT_ACTION LEVELS, and organism info
Run with: python3 manage.py shell < import_complete_data.py
"""

import pandas as pd
import numpy as np
from datetime import datetime
from decimal import Decimal
from bioburden.models import Area, Lot, BioburdenData, FixedThreshold
from django.utils import timezone

print("=" * 80)
print("🔬 COMPLETE BIOBURDEN DATA IMPORT - ALL EXCEL SHEETS")
print("=" * 80)

# Clear existing data
print("\n⚠️  Clearing existing data...")
BioburdenData.objects.all().delete()
FixedThreshold.objects.all().delete()
Lot.objects.all().delete()
Area.objects.all().delete()
print("✓ Cleared")

# Read the Excel file
excel_file = 'BIOBURDEN DATA with EM 20260202.xlsx'

# ============================================================================
# 1. IMPORT LOT_MASTER (Lot details with organisms)
# ============================================================================
print("\n📦 Step 1: Importing LOT_MASTER data...")

df_lots = pd.read_excel(excel_file, sheet_name='LOT_MASTER')
df_lots.columns = df_lots.columns.str.strip()

lots_dict = {}
for index, row in df_lots.iterrows():
    try:
        if pd.isna(row['LOT VECTOR']):
            continue
        
        lot_number = str(row['LOT VECTOR']).strip()
        
        # Parse production date
        prod_date = None
        if 'DATE PRODUCTION' in row and not pd.isna(row['DATE PRODUCTION']):
            try:
                prod_date = pd.to_datetime(row['DATE PRODUCTION']).date()
            except:
                pass
        
        # Get organisms
        primary_org = str(row.get('PRIMARY_ORGANISM', '')).strip() if not pd.isna(row.get('PRIMARY_ORGANISM')) else None
        secondary_org = str(row.get('SECONDARY_ORGANISM', '')).strip() if not pd.isna(row.get('SECONDARY_ORGANISM')) else None
        tertiary_org = str(row.get('TERTIARY_ORGANISM', '')).strip() if not pd.isna(row.get('TERTIARY_ORGANISM')) else None
        
        lot, created = Lot.objects.get_or_create(
            lot_number=lot_number,
            defaults={
                'product_name': 'Vector Product',
                'production_date': prod_date,
                'primary_organism': primary_org,
                'secondary_organism': secondary_org,
                'tertiary_organism': tertiary_org
            }
        )
        
        # Update if already exists
        if not created:
            lot.production_date = prod_date
            lot.primary_organism = primary_org
            lot.secondary_organism = secondary_org
            lot.tertiary_organism = tertiary_org
            lot.save()
        
        lots_dict[lot_number] = lot
        
        if created:
            org_info = f" - Organisms: {primary_org}" if primary_org else ""
            print(f"  ✓ {lot_number}{org_info}")
    
    except Exception as e:
        print(f"  ⚠️  Error with lot {row.get('LOT VECTOR')}: {e}")

print(f"✓ Processed {len(lots_dict)} lots from LOT_MASTER")

# ============================================================================
# 2. IMPORT RAW DATA (Bioburden Tests)
# ============================================================================
print("\n📊 Step 2: Importing bioburden test data from RAW DATA...")

df_raw = pd.read_excel(excel_file, sheet_name='RAW DATA')
df_raw.columns = df_raw.columns.str.strip()

# Create areas
areas_dict = {}
area_names = df_raw['AREA TESTED'].dropna().unique()
for area_name in area_names:
    area, created = Area.objects.get_or_create(
        name=str(area_name).strip(),
        defaults={'description': f'Testing area: {area_name}'}
    )
    areas_dict[str(area_name).strip()] = area
    if created:
        print(f"  ✓ Created area: {area_name}")

# Create any lots not in LOT_MASTER
for lot_num in df_raw['LOT VECTOR'].dropna().unique():
    lot_str = str(lot_num).strip()
    if lot_str not in lots_dict:
        lot, created = Lot.objects.get_or_create(
            lot_number=lot_str,
            defaults={'product_name': 'Product Vector'}
        )
        lots_dict[lot_str] = lot
        if created:
            print(f"  ✓ Created lot from RAW DATA: {lot_str}")

# Import bioburden test data
print("\n📝 Processing bioburden test records...")
test_count = 0
error_count = 0

for index, row in df_raw.iterrows():
    try:
        if pd.isna(row['LOT VECTOR']) or pd.isna(row['AREA TESTED']) or pd.isna(row['DATE']):
            continue
        
        lot_number = str(row['LOT VECTOR']).strip()
        area_name = str(row['AREA TESTED']).strip()
        
        lot = lots_dict.get(lot_number)
        area = areas_dict.get(area_name)
        
        if not lot or not area:
            continue
        
        test_date = pd.to_datetime(row['DATE']).date()
        
        correction_factor = row.get('CORRECTION FACTOR', 1.0)
        if pd.isna(correction_factor):
            correction_factor = 1.0
        
        provider = str(row.get('PROVIDER', 'External Lab'))
        validation = str(row.get('VALIDATION', 'NO'))
        
        # Process AEROBES samples
        aerobe_columns = [f'CFU AEROBES S{i}' for i in range(1, 11)]
        aerobe_values = [float(row[col]) for col in aerobe_columns if col in row and not pd.isna(row[col])]
        
        if aerobe_values:
            avg_cfu = sum(aerobe_values) / len(aerobe_values)
            
            BioburdenData.objects.create(
                lot=lot,
                area=area,
                test_date=test_date,
                sample_id=f"AEROBES-{test_date.strftime('%Y%m%d')}-{lot_number}",
                cfu_count=Decimal(str(round(avg_cfu, 2))),
                dilution_factor=Decimal(str(correction_factor)),
                lab_name=provider,
                analyst='Lab Analyst',
                notes=f"Type: AEROBES, Validation: {validation}, Samples: {len(aerobe_values)}, Min: {min(aerobe_values)}, Max: {max(aerobe_values)}"
            )
            test_count += 1
        
        # Process FUNGI samples
        fungi_columns = [f'CFU FUNGI S{i}' for i in range(1, 11)]
        fungi_values = []
        
        for col in fungi_columns:
            if col in row and not pd.isna(row[col]):
                val = float(row[col])
                if val > 1000:  # Filter out baseline values
                    fungi_values.append(val)
        
        if fungi_values:
            avg_fungi = sum(fungi_values) / len(fungi_values)
            
            BioburdenData.objects.create(
                lot=lot,
                area=area,
                test_date=test_date,
                sample_id=f"FUNGI-{test_date.strftime('%Y%m%d')}-{lot_number}",
                cfu_count=Decimal(str(round(avg_fungi, 2))),
                dilution_factor=Decimal(str(correction_factor)),
                lab_name=provider,
                analyst='Lab Analyst',
                notes=f"Type: FUNGI, Validation: {validation}, Samples: {len(fungi_values)}, Min: {min(fungi_values)}, Max: {max(fungi_values)}"
            )
            test_count += 1
    
    except Exception as e:
        error_count += 1
        if error_count <= 3:
            print(f"  ⚠️  Row {index}: {str(e)}")

print(f"✓ Imported {test_count} bioburden test records")
if error_count > 0:
    print(f"⚠️  {error_count} rows skipped due to errors")

# ============================================================================
# 3. IMPORT ALERT_ACTION LEVELS (Fixed Thresholds)
# ============================================================================
print("\n🚨 Step 3: Importing fixed alert/action levels...")

df_thresholds = pd.read_excel(excel_file, sheet_name='ALERT_ACTION LEVELS')
df_thresholds.columns = df_thresholds.columns.str.strip()

# Get the most recent threshold (2026)
if len(df_thresholds) > 0:
    latest_threshold = df_thresholds.iloc[-1]
    
    alert_level = latest_threshold.get('ALERT LEVEL FIXED')
    action_level = latest_threshold.get('ACTION LEVEL FIXED')
    period = latest_threshold.get('DATE PERIOD', 'Current')
    
    if not pd.isna(alert_level) and not pd.isna(action_level):
        print(f"  Using threshold period: {period}")
        print(f"  Alert Level:  {alert_level}")
        print(f"  Action Level: {action_level}")
        
        threshold_count = 0
        for lot in Lot.objects.all():
            FixedThreshold.objects.create(
                lot=lot,
                alert_level=Decimal(str(alert_level)),
                action_level=Decimal(str(action_level)),
                notes=f"Period: {period}, VDMAX: {latest_threshold.get('VDMAX DOSE', 'N/A')}"
            )
            threshold_count += 1
        
        print(f"✓ Created {threshold_count} fixed thresholds")

# ============================================================================
# 4. CALCULATE STATUS FOR ALL TESTS
# ============================================================================
print("\n🔄 Step 4: Calculating status based on thresholds...")

for test in BioburdenData.objects.all():
    test.save()

status_counts = {
    'normal': BioburdenData.objects.filter(status='normal').count(),
    'alert': BioburdenData.objects.filter(status='alert').count(),
    'action': BioburdenData.objects.filter(status='action').count(),
}

print(f"\n📊 Status Distribution:")
print(f"  🟢 Normal:  {status_counts['normal']} tests")
print(f"  🟠 Alert:   {status_counts['alert']} tests")
print(f"  🔴 Action:  {status_counts['action']} tests")

# ============================================================================
# 5. SUMMARY STATISTICS
# ============================================================================
print("\n" + "=" * 80)
print("✅ COMPLETE IMPORT SUCCESSFUL!")
print("=" * 80)

print(f"\n📈 Final Summary:")
print(f"  • Lots imported:        {Lot.objects.count()}")
print(f"    - With organisms:     {Lot.objects.exclude(primary_organism__isnull=True).count()}")
print(f"  • Testing areas:        {Area.objects.count()}")
areas_list = list(Area.objects.values_list('name', flat=True))
for area in areas_list:
    count = BioburdenData.objects.filter(area__name=area).count()
    print(f"    - {area}: {count} tests")

print(f"\n  • Bioburden tests:      {BioburdenData.objects.count()}")
print(f"    - AEROBES:            {BioburdenData.objects.filter(sample_id__contains='AEROBES').count()}")
print(f"    - FUNGI:              {BioburdenData.objects.filter(sample_id__contains='FUNGI').count()}")

print(f"\n  • Fixed thresholds:     {FixedThreshold.objects.count()}")
print(f"    - Alert level:        {alert_level}")
print(f"    - Action level:       {action_level}")

# Date range
first_test = BioburdenData.objects.order_by('test_date').first()
last_test = BioburdenData.objects.order_by('-test_date').first()
if first_test and last_test:
    print(f"\n  • Date range:           {first_test.test_date} to {last_test.test_date}")

print(f"\n🎯 All relevant data from Excel imported successfully!")
print(f"   View at: http://localhost:8000")
print("=" * 80)
