#!/bin/bash

echo "═══════════════════════════════════════════════════════"
echo "   🧫 BIOBURDEN MANAGEMENT SYSTEM"
echo "═══════════════════════════════════════════════════════"
echo ""

cd /Users/abdulmannan/Desktop/bioburden_web_app

# Check if database exists
if [ ! -f "db.sqlite3" ]; then
    echo "⚠️  Database not found. Please run setup first:"
    echo "   ./setup.sh"
    exit 1
fi

echo "🚀 Starting Bioburden Management Server..."
echo ""
echo "📍 Access Points:"
echo "   • Main App:  http://localhost:8000"
echo "   • Admin:     http://localhost:8000/admin"
echo ""
echo "📊 Features Ready:"
echo "   ✓ Dashboard with statistics"
echo "   ✓ Excel data import"
echo "   ✓ Visual alerts (🟢 🟠 🔴)"
echo "   ✓ Fixed thresholds"
echo "   ✓ Lot analysis"
echo "   ✓ Area comparison"
echo ""
echo "💡 Demo Tips:"
echo "   1. Start at Dashboard: http://localhost:8000"
echo "   2. Import data: Click 'Import' button"
echo "   3. Set thresholds: Click 'Thresholds' menu"
echo "   4. View lot details: Click any lot number"
echo ""
echo "⌨️  Press Ctrl+C to stop the server"
echo ""
echo "═══════════════════════════════════════════════════════"
echo ""

# Start Django development server
python3 manage.py runserver
