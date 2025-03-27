from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import EggFarm

class EggFarmForm(forms.ModelForm):
    class Meta:
        model = EggFarm
        fields = '__all__'
        widgets = {
            # Identification
            'supplier_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Sunny Acres Farm Inc.'}),
            'farm_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Green Valley Poultry'}),
            'site_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., North Barn Facility'}),
            'hen_house_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., House A-12'}),

            # Population and Breed
            'current_number_of_hens': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Total number of hens (e.g., 500)'}),
            'average_age_weeks': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Average hen age in weeks (e.g., 32.5)'}),
            'breed': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Select primary hen breed'}),
            'breed_percentage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Percentage of primary breed (0-100)'}),

            # Production
            'daily_egg_production': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Daily egg production in dozens (e.g., 45.5)'}),
            'weekly_egg_production': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Weekly egg production in dozens (e.g., 318)'}),
            'small_eggs_percentage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Percentage of small eggs (0-100)'}),
            'medium_eggs_percentage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Percentage of medium eggs (0-100)'}),
            'large_eggs_percentage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Percentage of large eggs (0-100)'}),
            'extra_large_eggs_percentage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Percentage of extra large eggs (0-100)'}),
            'jumbo_eggs_percentage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Percentage of jumbo eggs (0-100)'}),
            'defective_eggs_percentage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Percentage of defective eggs (0-100)'}),
            'first_grade_egg_percentage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Percentage of first-grade eggs (0-100)'}),

            # Feed & Water
            'average_feed_consumption': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Feed consumption in g/hen/day (e.g., 120.5)'}),
            'average_water_intake': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Water intake in L/hen/day (e.g., 0.25)'}),

            # Mortality
            'weekly_mortality_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Weekly mortality rate (0-100)'}),
            'total_mortality': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Total number of hens that have died'}),
            'hens_culled': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Number of hens removed from flock'}),
            'expected_cull_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'placeholder': 'Expected date for flock replacement'}),

            # Placement
            'recent_placement_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'placeholder': 'Date of most recent hen placement'}),
            'age_of_pullets_at_placement': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Age of pullets at placement (weeks)'}),
            'upcoming_placement_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'placeholder': 'Planned date for next flock placement'}),

            # Health
            'health_issues': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Are there current health issues?'}),
            'recent_vaccinations': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'List recent vaccinations (date, type, etc.)'}),
            'next_vaccination_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'placeholder': 'Scheduled date for next vaccination'}),

            # Market
            'time_to_distribution': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Days from egg collection to distribution'}),
            'market_condition_notes': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Notes on current market conditions affecting production'}),
            'weekly_production_trend': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Percentage change in production compared to last week'}),
            'seasonal_trend_notes': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Notes on seasonal production trends'}),
        }

    def clean(self):
        cleaned_data = super().clean()

        # Egg size validation
        total = sum([
            cleaned_data.get('small_eggs_percentage', 0),
            cleaned_data.get('medium_eggs_percentage', 0),
            cleaned_data.get('large_eggs_percentage', 0),
            cleaned_data.get('extra_large_eggs_percentage', 0),
            cleaned_data.get('jumbo_eggs_percentage', 0),
        ])
        if abs(total - 100) > 0.1:
            raise ValidationError("Egg size distribution percentages must total 100%")

        # Logical population check
        hens = cleaned_data.get('current_number_of_hens', 0)
        mortality = cleaned_data.get('total_mortality', 0)
        culled = cleaned_data.get('hens_culled', 0)
        if hens + mortality + culled <= 0:
            raise ValidationError("Hen population and losses cannot all be zero.")

        # Production logic
        daily = cleaned_data.get('daily_egg_production', 0)
        weekly = cleaned_data.get('weekly_egg_production', 0)
        if weekly and abs(daily * 7 - weekly) > (daily * 0.5):
            raise ValidationError("Weekly egg production should be close to daily * 7.")

        return cleaned_data

class UploadFileForm(forms.Form):
    file = forms.FileField(label="Upload CSV or Excel file")

    def clean_file(self):
        uploaded_file = self.cleaned_data.get('file')
        if not uploaded_file.name.endswith(('.csv', '.xlsx')):
            raise ValidationError("Only CSV or Excel files are allowed.")
        return uploaded_file

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']