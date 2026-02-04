from django import forms
from .models import BioburdenData, FixedThreshold, Area, Lot, DataImport


class DataImportForm(forms.ModelForm):
    """Form for uploading Excel files"""
    class Meta:
        model = DataImport
        fields = ['uploaded_file', 'imported_by']
        widgets = {
            'uploaded_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.xlsx,.xls'
            }),
            'imported_by': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your name (optional)'
            })
        }


class BioburdenDataForm(forms.ModelForm):
    """Form for manual bioburden data entry"""
    class Meta:
        model = BioburdenData
        fields = ['lot', 'area', 'test_date', 'sample_id', 'cfu_count', 
                  'dilution_factor', 'lab_name', 'analyst', 'notes']
        widgets = {
            'test_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'lot': forms.Select(attrs={'class': 'form-control'}),
            'area': forms.Select(attrs={'class': 'form-control'}),
            'sample_id': forms.TextInput(attrs={'class': 'form-control'}),
            'cfu_count': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'dilution_factor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'lab_name': forms.TextInput(attrs={'class': 'form-control'}),
            'analyst': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class FixedThresholdForm(forms.ModelForm):
    """Form for setting fixed alert/action levels"""
    class Meta:
        model = FixedThreshold
        fields = ['lot', 'area', 'alert_level', 'action_level', 'notes']
        widgets = {
            'lot': forms.Select(attrs={'class': 'form-control'}),
            'area': forms.Select(attrs={'class': 'form-control'}),
            'alert_level': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'action_level': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class FilterForm(forms.Form):
    """Form for filtering dashboard data"""
    lot = forms.ModelChoiceField(
        queryset=Lot.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    area = forms.ModelChoiceField(
        queryset=Area.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    status = forms.ChoiceField(
        choices=[('', 'All')] + BioburdenData.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
