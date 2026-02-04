"""
Sample data loader for demonstration purposes
Run with: python manage.py shell < load_sample_data.py
"""

from bioburden.models import Area, Lot, BioburdenData, FixedThreshold
from datetime import datetime, timedelta
from decimal import Decimal

print("🔧 Creating sample data for demonstration...")

# Create Areas
areas_data = [
    {"name": "Clean Room A", "description": "Primary sterile manufacturing area"},
    {"name": "Clean Room B", "description": "Secondary processing area"},
    {"name": "Packaging Area", "description": "Final product packaging"},
]

areas = {}
for area_data in areas_data:
    area, created = Area.objects.get_or_create(
        name=area_data["name"],
        defaults={"description": area_data["description"]}
    )
    areas[area.name] = area
    if created:
        print(f"✓ Created area: {area.name}")

# Create Lots
lots_data = [
    {"lot_number": "LOT-2024-001", "product_name": "Product A"},
    {"lot_number": "LOT-2024-002", "product_name": "Product A"},
    {"lot_number": "LOT-2024-003", "product_name": "Product B"},
    {"lot_number": "LOT-2024-004", "product_name": "Product B"},
]

lots = {}
for lot_data in lots_data:
    lot, created = Lot.objects.get_or_create(
        lot_number=lot_data["lot_number"],
        defaults={"product_name": lot_data["product_name"]}
    )
    lots[lot.lot_number] = lot
    if created:
        print(f"✓ Created lot: {lot.lot_number}")

# Create Fixed Thresholds
thresholds_data = [
    {"lot": "LOT-2024-001", "alert": 50, "action": 100},
    {"lot": "LOT-2024-002", "alert": 45, "action": 90},
    {"lot": "LOT-2024-003", "alert": 55, "action": 110},
    {"lot": "LOT-2024-004", "alert": 50, "action": 100},
]

for threshold_data in thresholds_data:
    lot = lots[threshold_data["lot"]]
    threshold, created = FixedThreshold.objects.get_or_create(
        lot=lot,
        defaults={
            "alert_level": Decimal(threshold_data["alert"]),
            "action_level": Decimal(threshold_data["action"]),
            "notes": "Demo threshold"
        }
    )
    if created:
        print(f"✓ Created threshold for {lot.lot_number}")

# Create Sample Bioburden Data
print("\n📊 Creating sample test data...")

base_date = datetime.now() - timedelta(days=30)
test_count = 0

for i in range(30):
    test_date = base_date + timedelta(days=i)
    
    for lot_number, lot in lots.items():
        for area_name, area in areas.items():
            # Generate varying CFU values
            import random
            base_cfu = random.uniform(20, 120)
            
            # Add some spikes for demo
            if random.random() > 0.8:
                base_cfu = random.uniform(80, 150)
            
            BioburdenData.objects.create(
                lot=lot,
                area=area,
                test_date=test_date.date(),
                sample_id=f"SAMPLE-{test_date.strftime('%Y%m%d')}-{lot_number[-3:]}",
                cfu_count=Decimal(str(round(base_cfu, 2))),
                dilution_factor=Decimal("1.0"),
                lab_name="External Testing Lab",
                analyst="Lab Analyst",
                notes="Demo data"
            )
            test_count += 1

print(f"✓ Created {test_count} test records")

print("\n✅ Sample data loaded successfully!")
print("\n🎯 You can now:")
print("   1. View the dashboard")
print("   2. See color-coded alerts")
print("   3. Analyze lot trends")
print("   4. Compare areas")
