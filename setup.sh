#!/bin/bash

echo "🚀 Setting up Bioburden Management Application..."
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create directories
echo "📁 Creating media directory..."
mkdir -p media/imports

# Make migrations
echo "🗄️  Setting up database..."
python manage.py makemigrations bioburden
python manage.py migrate

# Create superuser prompt
echo ""
echo "👤 Create an admin user:"
python manage.py createsuperuser

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 To start the server, run:"
echo "   python manage.py runserver"
echo ""
echo "📍 Then open your browser to:"
echo "   http://localhost:8000"
echo ""
echo "🔐 Admin panel:"
echo "   http://localhost:8000/admin"
echo ""
