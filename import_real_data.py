"""
Import actual bioburden data from the client's Excel file
Run with: python3 manage.py shell < import_real_data.py
"""

import pandas as pd
import numpy as np
from datetime import datetime
from decimal import Decimal
from bioburden.models import Area, Lot, BioburdenData, FixedThreshold
from django.utils import timezone

print("=" * 80)
print("🔬 IMPORTING ACTUAL BIOBURDEN DATA")
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
# IMPORT RAW DATA (Bioburden Tests)
# ============================================================================
print("\n📊 Importing bioburden test data from RAW DATA sheet...")

df_raw = pd.read_excel(excel_file, sheet_name='RAW DATA')

# Clean column names
df_raw.columns = df_raw.columns.str.strip()

# Get unique areas and create them
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

# Get unique lots and create them
lots_dict = {}
lot_numbers = df_raw['LOT VECTOR'].dropna().unique()
for lot_num in lot_numbers:
    lot, created = Lot.objects.get_or_create(
        lot_number=str(lot_num).strip(),
        defaults={'product_name': 'Product Vector'}
    )
    lots_dict[str(lot_num).strip()] = lot
    if created:
        print(f"  ✓ Created lot: {lot_num}")

# Import bioburden test data
print("\n📝 Processing test records...")
test_count = 0
error_count = 0

for index, row in df_raw.iterrows():
    try:
        # Skip if essential data is missing
        if pd.isna(row['LOT VECTOR']) or pd.isna(row['AREA TESTED']) or pd.isna(row['DATE']):
            continue
        
        lot_number = str(row['LOT VECTOR']).strip()
        area_name = str(row['AREA TESTED']).strip()
        
        # Get lot and area
        lot = lots_dict.get(lot_number)
        area = areas_dict.get(area_name)
        
        if not lot or not area:
            continue
        
        # Parse date
        test_date = pd.to_datetime(row['DATE']).date()
        
        # Get correction factor (dilution)
        correction_factor = row.get('CORRECTION FACTOR', 1.0)
        if pd.isna(correction_factor):
            correction_factor = 1.0
        
        # Process AEROBES samples (S1-S10)
        aerobe_columns = [f'CFU AEROBES S{i}' for i in range(1, 11)]
        aerobe_values = []
        
        for col in aerobe_columns:
            if col in row and not pd.isna(row[col]):
                aerobe_values.append(float(row[col]))
        
        # If we have aerobe values, calculate average
        if aerobe_values:
            avg_cfu = sum(aerobe_values) / len(aerobe_values)
            
            # Create bioburden data record for AEROBES
            BioburdenData.objects.create(
                lot=lot,
                area=area,
                test_date=test_date,
                sample_id=f"AEROBES-{test_date.strftime('%Y%m%d')}-{lot_number}",
                cfu_count=Decimal(str(round(avg_cfu, 2))),
                dilution_factor=Decimal(str(correction_factor)),
                lab_name=row.get('PROVIDER', 'External Lab'),
                analyst='Lab Analyst',
                notes=f"Validation: {row.get('VALIDATION', 'N/A')}, Samples: {len(aerobe_values)}"
            )
            test_count += 1
        
        # Process FUNGI samples (S1-S10)
        fungi_columns = [f'CFU FUNGI S{i}' for i in range(1, 11)]
        fungi_values = []
        
        for col in fungi_columns:
            if col in row and not pd.isna(row[col]):
                val = float(row[col])
                # Only include if not 1000 (appears to be default/baseline)
                if val > 1000:
                    fungi_values.append(val)
        
        # If we have significant fungi values, create record
        if fungi_values:
            avg_fungi = sum(fungi_values) / len(fungi_values)
            
            BioburdenData.objects.create(
                lot=lot,
                area=area,
                test_date=test_date,
                sample_id=f"FUNGI-{test_date.strftime('%Y%m%d')}-{lot_number}",
                cfu_count=Decimal(str(round(avg_fungi, 2))),
                dilution_factor=Decimal(str(correction_factor)),
                lab_name=row.get('PROVIDER', 'External Lab'),
                analyst='Lab Analyst',
                notes=f"FUNGI test, Samples: {len(fungi_values)}"
            )
            test_count += 1
        
    except Exception as e:
        error_count += 1
        if error_count <= 5:  # Only print first 5 errors
            print(f"  ⚠️  Row {index}: {str(e)}")

print(f"\n✓ Imported {test_count} test records")
if error_count > 0:
    print(f"⚠️  {error_count} rows had errors (skipped)")

# ============================================================================
# IMPORT ALERT_ACTION LEVELS (Fixed Thresholds)
# ============================================================================
print("\n🚨 Importing fixed alert/action levels...")

df_thresholds = pd.read_excel(excel_file, sheet_name='ALERT_ACTION LEVELS')
df_thresholds.columns = df_thresholds.columns.str.strip()

# Get the most recent threshold values (last row)
if len(df_thresholds) > 0:
    latest_threshold = df_thresholds.iloc[-1]
    
    alert_level = latest_threshold.get('ALERT LEVEL FIXED')
    action_level = latest_threshold.get('ACTION LEVEL FIXED')
    
    if not pd.isna(alert_level) and not pd.isna(action_level):
        print(f"  Using latest thresholds: Alert={alert_level}, Action={action_level}")
        
        # Apply to all lots
        threshold_count = 0
        for lot in Lot.objects.all():
            FixedThreshold.objects.create(
                lot=lot,
                alert_level=Decimal(str(alert_level)),
                action_level=Decimal(str(action_level)),
                notes=f"From ALERT_ACTION LEVELS sheet, period: {latest_threshold.get('DATE PERIOD', 'N/A')}"
            )
            threshold_count += 1
        
        print(f"✓ Created {threshold_count} fixed thresholds (one per lot)")

# ============================================================================
# UPDATE STATUS FOR ALL TESTS
# ============================================================================
print("\n🔄 Calculating status for all tests based on thresholds...")

for test in BioburdenData.objects.all():
    test.save()  # This triggers the status calculation

status_counts = {
    'normal': BioburdenData.objects.filter(status='normal').count(),
    'alert': BioburdenData.objects.filter(status='alert').count(),
    'action': BioburdenData.objects.filter(status='action').count(),
}

print(f"\n📊 Status Distribution:")
print(f"  🟢 Normal:  {status_counts['normal']}")
print(f"  🟠 Alert:   {status_counts['alert']}")
print(f"  🔴 Action:  {status_counts['action']}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("✅ IMPORT COMPLETE!")
print("=" * 80)
print(f"\n📈 Summary:")
print(f"  • Areas created:     {Area.objects.count()}")
print(f"  • Lots created:      {Lot.objects.count()}")
print(f"  • Tests imported:    {BioburdenData.objects.count()}")
print(f"  • Thresholds set:    {FixedThreshold.objects.count()}")
print(f"\n🎯 Your actual bioburden data is now loaded!")
print(f"   Open http://localhost:8000 to view the dashboard\n")
print("=" * 80)
