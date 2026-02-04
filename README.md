# Bioburden Management Web Application

A modern Django-based web application for managing and analyzing bioburden test data, replacing complex Excel spreadsheets with an intuitive, automated system.

## 🌟 Key Features

### ✅ **Data Management**
- Import bioburden data directly from Excel files
- Automatic detection of data sheets and thresholds
- Manual data entry with form validation
- Track data by Lot, Area, and Test Date

### 📊 **Analysis & Visualization**
- Interactive dashboard with real-time statistics
- Chart.js powered visualizations
- Time-series trend analysis with threshold lines
- Area-by-area comparison reports
- Lot-specific detailed views

### 🚨 **Alert System**
- **Fixed Alert & Action Levels** - Define custom thresholds per lot
- **Visual Indicators**:
  - 🟢 Green = Normal (within limits)
  - 🟠 Orange = Alert Level Exceeded
  - 🔴 Red = Action Level Exceeded
- Automatic status calculation on data save
- Dashboard alerts for tests requiring attention

### 📈 **Advanced Analytics**
- Calculate average bioburden levels
- Compare bioburden between different areas
- Statistical summaries (mean, max, min, std dev)
- Historical trend tracking
- Export-ready data tables

### 🔧 **Easy Integration**
- Import from existing Excel files
- Reference table support for fixed thresholds
- Bulk data import with error handling
- Data validation and cleanup

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)

### Installation

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Initialize Database**
```bash
python manage.py makemigrations
python manage.py migrate
```

3. **Create Admin User**
```bash
python manage.py createsuperuser
```

4. **Run Development Server**
```bash
python manage.py runserver
```

5. **Access Application**
- Main App: http://localhost:8000
- Admin Panel: http://localhost:8000/admin

## 📁 Project Structure

```
bioburden_web_app/
├── bioburden/              # Main application
│   ├── models.py          # Data models (BioburdenData, FixedThreshold, etc.)
│   ├── views.py           # View logic and controllers
│   ├── forms.py           # Form definitions
│   ├── utils.py           # Excel import utilities
│   ├── admin.py           # Admin interface configuration
│   └── urls.py            # URL routing
├── bioburden_project/     # Project settings
│   ├── settings.py        # Django settings
│   └── urls.py            # Main URL configuration
├── templates/             # HTML templates
│   ├── base.html          # Base template with navigation
│   └── bioburden/         # App-specific templates
├── static/                # Static files (CSS, JS, images)
├── media/                 # Uploaded files
├── manage.py              # Django management script
└── requirements.txt       # Python dependencies
```

## 📊 Data Models

### **BioburdenData**
Main test data from laboratory:
- Lot number
- Testing area
- Test date
- CFU count (Colony Forming Units)
- Dilution factor
- Adjusted CFU (calculated)
- Status (normal/alert/action)
- Laboratory info
- Notes

### **FixedThreshold**
Alert and action levels per lot:
- Lot reference
- Alert level (orange threshold)
- Action level (red threshold)
- Optional area specification
- Notes

### **Area**
Testing locations:
- Area name
- Description

### **Lot**
Product lots:
- Lot number
- Product name
- Manufacture date

## 📥 Excel Import Format

### Bioburden Data Sheet
Required columns:
- `Lot` - Lot number
- `Area` - Testing area name
- `Test Date` or `Date` - Date of test
- `CFU` or `CFU Count` - Colony count

Optional columns:
- `Dilution` - Dilution factor (default: 1.0)
- `Sample ID` - Sample identifier
- `Laboratory` - Lab name
- `Analyst` - Analyst name
- `Product` - Product name
- `Notes` - Additional notes

### Thresholds Sheet (Optional)
Required columns:
- `Lot` - Lot number
- `Alert Level` or `Alert` - Orange threshold value
- `Action Level` or `Action` - Red threshold value

Optional columns:
- `Area` - Specific area (leave blank for all)
- `Notes` - Additional information

## 🎯 Usage Guide

### 1. Import Existing Data
1. Go to **Import** page
2. Upload your Excel file
3. System automatically detects and imports data
4. Review import results

### 2. Set Fixed Thresholds
1. Navigate to **Thresholds**
2. Click **Add Threshold**
3. Select lot and enter alert/action levels
4. Tests are automatically color-coded

### 3. View Dashboard
- See overall statistics
- Monitor alerts and actions
- View recent tests
- Analyze trends

### 4. Analyze by Lot
1. Click on any lot number
2. View all tests for that lot
3. See trend chart with threshold lines
4. Review statistics

### 5. Compare Areas
- Navigate to **Area Comparison**
- See side-by-side metrics
- Identify problematic areas

## 🎨 Visual Alert System

The application uses color-coded badges throughout:

- **🟢 Green (Normal)**: CFU < Alert Level
- **🟠 Orange (Alert)**: Alert Level ≤ CFU < Action Level
- **🔴 Red (Action)**: CFU ≥ Action Level

Alerts appear in:
- Dashboard statistics
- Data tables
- Lot detail charts
- Area comparisons

## 🔐 Admin Interface

Access advanced features at `/admin`:
- Bulk data operations
- Direct database editing
- User management
- Data export

## 🔄 Workflow Example

1. **Weekly Data Upload**
   - Laboratory sends Excel file
   - Upload via Import page
   - System validates and imports
   - Automatic status calculation

2. **Review Alerts**
   - Check dashboard for orange/red alerts
   - Click through to lot details
   - Review trend charts
   - Take corrective action

3. **Monthly Analysis**
   - Use Area Comparison
   - Export filtered data
   - Review statistics
   - Update thresholds if needed

## 💡 Benefits Over Excel

### ✅ **Advantages**
1. **No Manual Formulas** - Automatic calculations
2. **Data Validation** - Prevents errors at input
3. **Visual Alerts** - Immediate identification of issues
4. **Historical Tracking** - All data in one place
5. **Multi-User Access** - Team collaboration
6. **Searchable/Filterable** - Find data instantly
7. **Professional Reports** - Export-ready views
8. **No Version Control Issues** - Single source of truth
9. **Scalable** - Handles thousands of records
10. **Backup & Security** - Database-backed storage

### 📉 **Excel Pain Points Solved**
- ❌ ~~Broken formulas~~ → ✅ Automatic calculations
- ❌ ~~Manual linking~~ → ✅ Database relationships
- ❌ ~~Copy-paste errors~~ → ✅ Form validation
- ❌ ~~Multiple versions~~ → ✅ Single system
- ❌ ~~Limited visualizations~~ → ✅ Interactive charts
- ❌ ~~No audit trail~~ → ✅ Timestamped records

## 🚀 Deployment Options

### Local/Network Server
```bash
# For production, use gunicorn
pip install gunicorn
gunicorn bioburden_project.wsgi:application
```

### Cloud Deployment
Compatible with:
- **Heroku** - Easy deployment
- **AWS** - Scalable infrastructure
- **DigitalOcean** - Simple VPS
- **PythonAnywhere** - Quick hosting

## 🛠️ Customization

### Add New Fields
Edit `bioburden/models.py` and run:
```bash
python manage.py makemigrations
python manage.py migrate
```

### Modify Thresholds Logic
Edit the `save()` method in `BioburdenData` model

### Custom Reports
Add new views in `bioburden/views.py`

## 📞 Support & Documentation

### Common Tasks

**Reset Database:**
```bash
rm db.sqlite3
python manage.py migrate
```

**Create Sample Data:**
```bash
python manage.py shell
# Import and create test data
```

**Backup Database:**
```bash
cp db.sqlite3 backup_$(date +%Y%m%d).sqlite3
```

## 📝 License

This project is created for bioburden management and analysis.

## 🎉 Demo Ready

The application is ready to demonstrate to your client:

1. ✅ Clean, professional interface
2. ✅ Intuitive navigation
3. ✅ Automatic Excel import
4. ✅ Visual alert system (orange/red)
5. ✅ Fixed threshold support
6. ✅ Lot-based tracking
7. ✅ Area comparisons
8. ✅ Interactive charts
9. ✅ Mobile-responsive design
10. ✅ Production-ready code

---

**Ready to replace Excel with a modern web solution!** 🚀
# bioburden_management_webapp
