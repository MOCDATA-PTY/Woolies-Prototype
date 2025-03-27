# Django Core Imports
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import Sum, Avg, Count, F
from django.db.models.functions import TruncWeek

# Forms & Models
from .forms import EggFarmForm, UserForm
from .models import EggFarm

# Forecasting & Analysis
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from datetime import datetime, timedelta

# File Handling
import csv
import openpyxl
from openpyxl.utils import get_column_letter
from io import StringIO, BytesIO, TextIOWrapper
from zipfile import ZipFile

# Scientific & Statistical Computing
from scipy import stats

# Utilities
import traceback
import logging

# Custom Decorators
from .decorators import critical_view_decorator

# Logging Configuration
logger = logging.getLogger(__name__)









# Decorator to ensure re-authentication for critical views


from django.views.decorators.http import require_http_methods
from django.core.files.storage import FileSystemStorage


import traceback
import csv
import openpyxl
from io import TextIOWrapper
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required





def debug_forecast_data(request):
    farms = EggFarm.objects.all()
    total_farms = farms.count()
    farms_with_production = farms.filter(weekly_egg_production__isnull=False, weekly_egg_production__gt=0)

    if farms.exists():
        earliest_record = farms.earliest('production_date').production_date
        latest_record = farms.latest('production_date').production_date
    else:
        earliest_record = latest_record = None

    weekly_data = (
        farms
        .annotate(week=TruncWeek('production_date'))
        .values('week')
        .annotate(
            total_production=Sum('weekly_egg_production'),
            farm_count=Count('id')
        )
        .order_by('week')
    )

    context = {
        'total_farms': total_farms,
        'farms_with_production': farms_with_production.count(),
        'earliest_record': earliest_record,
        'latest_record': latest_record,
        'weekly_data': list(weekly_data)
    }

    return JsonResponse(context)




@login_required
def test_dashboard(request):
    return render(request, 'main/dashboard_test.html')


@critical_view_decorator
@login_required(login_url='login')
@require_http_methods(["GET", "POST"])
def import_egg_farms(request):
    if request.method == 'POST' and request.FILES.get('data_file'):
        data_file = request.FILES['data_file']
        filename = data_file.name.lower()

        try:
            rows = []

            # ✅ Excel (.xlsx)
            if filename.endswith('.xlsx'):
                wb = openpyxl.load_workbook(data_file)
                sheet = wb.active
                rows = list(sheet.iter_rows(min_row=2, values_only=True))

            # ✅ CSV (.csv)
            elif filename.endswith('.csv'):
                decoded_file = data_file.read().decode('utf-8')
                lines = decoded_file.splitlines()

                if not lines:
                    raise ValueError("CSV file is empty.")

                reader = csv.reader(lines)
                header = next(reader, None)  # safely try to get header

                if not header:
                    raise ValueError("CSV file has no header row.")

                rows = list(reader)
                if not rows:
                    raise ValueError("CSV file contains only a header and no data.")

            else:
                messages.error(request, 'Unsupported file format. Please upload a .xlsx or .csv file.')
                return redirect('egg_farm_list')

            # ✅ Process rows
            results = process_import_rows(rows)
            generate_import_messages(request, results)
            return redirect('egg_farm_list')

        except Exception as e:
            error_message = f"Error processing file: {str(e)}"
            print("❌ FILE IMPORT ERROR ❌")
            traceback.print_exc()  # Print full stack trace
            messages.error(request, error_message)
            return redirect('egg_farm_list')

    return render(request, 'main/import_egg_farms.html')


def parse_date(date_val):
    """
    Safely parse Excel date values into Python date objects.
    Accepts strings or datetime objects.
    """
    from datetime import datetime, date

    if not date_val:
        return None

    if isinstance(date_val, (datetime, date)):
        return date_val.date() if isinstance(date_val, datetime) else date_val

    try:
        return datetime.strptime(str(date_val), '%Y-%m-%d').date()
    except ValueError:
        return None


def process_import_rows(rows):
    results = {
        'created': [],
        'updated': [],
        'skipped': [],
        'errors': []
    }

    for index, row in enumerate(rows):
        try:
            cleaned_data = validate_egg_farm_data(row)
            if not cleaned_data:
                results['errors'].append(f"[Row {index + 2}] Validation failed: {row}")
                continue

            with transaction.atomic():  # 🔐 Each row safely in its own transaction
                existing = EggFarm.objects.filter(
                    supplier_name=cleaned_data['supplier_name'],
                    farm_name=cleaned_data['farm_name'],
                    site_name=cleaned_data['site_name'],
                    hen_house_number=cleaned_data['hen_house_number'],
                ).first()

                if existing:
                    for key, value in cleaned_data.items():
                        setattr(existing, key, value)
                    existing.save()
                    results['updated'].append(existing)
                else:
                    new_farm = EggFarm.objects.create(**cleaned_data)
                    results['created'].append(new_farm)

        except Exception as e:
            results['errors'].append(f"[Row {index + 2}] Processing error: {e} | Data: {row}")

    return results
def generate_import_messages(request, results, debug=True):
    """
    Generate user-friendly messages based on import results.
    Prints error entries to console if debug=True.
    """
    if results['created']:
        messages.success(request, f'{len(results["created"])} new entries created.')
    
    if results['updated']:
        messages.info(request, f'{len(results["updated"])} entries updated.')
    
    if results['skipped']:
        messages.warning(request, f'{len(results["skipped"])} entries skipped.')

    if results['errors']:
        messages.error(
            request,
            f'{len(results["errors"])} entries could not be processed. '
            'Please check your file format and data.'
        )

        if debug:
            print("❌ DEBUG: Error Entries")
            for i, err in enumerate(results['errors'], 1):
                print(f"Error {i}: {err}")

    if not any(results.values()):
        messages.warning(request, 'No entries were imported. File might be empty.')



def process_imported_data(rows):
    """
    Process imported data rows, handling duplicates and errors.
    """
    skipped_entries = []
    created_entries = 0
    error_entries = []

    expected_columns = 34  # Adjusted to match actual number of fields used

    for row in rows:
        try:
            # Validate row length matches expected header count
            if len(row) < expected_columns:
                error_entries.append(f"Incomplete row: {row}")
                continue

            # Data mapping based on your import template
            farm_data = {
                'supplier_name': row[0],
                'farm_name': row[1],
                'site_name': row[2],
                'hen_house_number': row[3],
                'current_number_of_hens': int(row[4] or 0),
                'average_age_weeks': float(row[5] or 0),
                'breed': row[6],
                'breed_percentage': float(row[7] or 0),
                'daily_egg_production': float(row[8] or 0),
                'weekly_egg_production': float(row[9] or 0),
                'small_eggs_percentage': float(row[10] or 0),
                'medium_eggs_percentage': float(row[11] or 0),
                'large_eggs_percentage': float(row[12] or 0),
                'extra_large_eggs_percentage': float(row[13] or 0),
                'jumbo_eggs_percentage': float(row[14] or 0),
                'defective_eggs_percentage': float(row[15] or 0),
                'first_grade_eggs_percentage': float(row[16] or 0),
                'average_feed_consumption': float(row[17] or 0),
                'average_water_intake': float(row[18] or 0),
                'weekly_mortality_rate': float(row[19] or 0),
                'total_mortality': int(row[20] or 0),
                'hens_culled': int(row[21] or 0),
                'expected_cull_date': None if not row[22] else datetime.datetime.strptime(row[22], '%Y-%m-%d').date(),
                'recent_placement_date': None if not row[23] else datetime.datetime.strptime(row[23], '%Y-%m-%d').date(),
                'age_of_pullets_at_placement': float(row[24] or 0),
                'upcoming_placement_date': None if not row[25] else datetime.datetime.strptime(row[25], '%Y-%m-%d').date(),
                'health_issues': row[26],
                'recent_vaccinations': row[27],
                'next_vaccination_date': None if not row[28] else datetime.datetime.strptime(row[28], '%Y-%m-%d').date(),
                'time_to_distribution': int(row[29] or 0),
                'market_condition_notes': row[30],
                'weekly_production_trend': float(row[31] or 0),
                'seasonal_trend_notes': row[32],
            }

            # Check for existing record to prevent duplicates
            existing_record = EggFarm.objects.filter(
                farm_name=farm_data['farm_name'],
                site_name=farm_data['site_name'],
                hen_house_number=farm_data['hen_house_number']
            ).first()

            if existing_record:
                skipped_entries.append(f"Duplicate entry: {farm_data['farm_name']} - {farm_data['site_name']}")
                continue

            # Create new EggFarm record
            egg_farm = EggFarm(**farm_data)
            egg_farm.save()
            created_entries += 1

        except Exception as e:
            error_entries.append(f"Error processing row {row}: {str(e)}")

    return skipped_entries, created_entries, error_entries

def clear_messages(request):
    """
    Helper function to clear all messages from the request.
    """
    storage = messages.get_messages(request)
    for message in storage:
        pass
    storage.used = True


@login_required(login_url='login')
def home(request):
    print("User authenticated:", request.user.is_authenticated)
    return render(request, 'main/home.html')



@critical_view_decorator
@login_required(login_url='login')
def add_egg_farm(request):
    """
    View to add a new egg farm record.
    Displays existing farm names for reference.
    """
    existing_farms = EggFarm.objects.values_list('farm_name', flat=True).distinct()

    if request.method == 'POST':
        form = EggFarmForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Egg farm record added successfully.')
            return redirect('egg_farm_list')
        else:
            print("Form errors:", form.errors)
            messages.error(request, 'Please correct the errors below.')
    else:
        form = EggFarmForm()

    return render(request, 'main/add_egg_farm.html', {
        'form': form,
        'farms': existing_farms
    })

@critical_view_decorator
@login_required(login_url='login')
def egg_farm_list(request):
    """
    List all egg farm records with advanced filtering options.
    """
    clear_messages(request)
    egg_farms = EggFarm.objects.all()
    
    # Advanced filtering
    farm_name = request.GET.get('farm_name')
    site_name = request.GET.get('site_name')
    breed = request.GET.get('breed')
    placement_from = request.GET.get('placement_from')
    placement_to = request.GET.get('placement_to')

    # Apply filters if provided
    if farm_name:
        egg_farms = egg_farms.filter(farm_name__icontains=farm_name)
    if site_name:
        egg_farms = egg_farms.filter(site_name__icontains=site_name)
    if breed:
        egg_farms = egg_farms.filter(breed=breed)
    if placement_from:
        egg_farms = egg_farms.filter(recent_placement_date__gte=placement_from)
    if placement_to:
        egg_farms = egg_farms.filter(recent_placement_date__lte=placement_to)
    
    # Get distinct farm names and breeds for filtering
    farm_names = EggFarm.objects.values_list('farm_name', flat=True).distinct().order_by('farm_name')
    breeds = EggFarm.BREED_CHOICES

    return render(request, 'main/egg_farm_list.html', {
        'egg_farms': egg_farms,
        'farm_names': farm_names,
        'breeds': breeds,
    })

@critical_view_decorator
@login_required(login_url='login')
def edit_egg_farm(request, pk):
    """
    Edit an existing egg farm record.
    Allows keeping the original record or updating.
    """
    clear_messages(request)
    egg_farm = get_object_or_404(EggFarm, pk=pk)
    
    # Option to keep original record
    if request.method == 'POST' and 'keep_original' in request.POST:
        messages.info(request, 'No changes were made to the record.')
        return redirect('egg_farm_list')
    
    if request.method == 'POST':
        form = EggFarmForm(request.POST, instance=egg_farm)
        if form.is_valid():
            form.save()
            messages.success(request, 'Egg farm record updated successfully.')
            return redirect('egg_farm_list')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = EggFarmForm(instance=egg_farm)
    return render(request, 'main/edit_egg_farm.html', {'form': form, 'egg_farm': egg_farm})

@critical_view_decorator
@login_required(login_url='login')
def delete_egg_farm(request, pk):
    """
    Delete a specific egg farm record.
    """
    clear_messages(request)
    egg_farm = get_object_or_404(EggFarm, pk=pk)
    if request.method == 'POST':
        egg_farm.delete()
        messages.success(request, 'Egg farm record deleted successfully.')
    return redirect('egg_farm_list')

@critical_view_decorator
@login_required(login_url='login')
def export_egg_farms(request):
    # In-memory ZIP file
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w') as zip_file:
        data = EggFarm.objects.all()

        # ====== 1. Create CSV content ======
        csv_string_io = StringIO()
        csv_writer = csv.writer(csv_string_io)

        header = [
            'Supplier Name', 'Farm Name', 'Site Name', 'Hen House Number',
            'Current Number of Hens', 'Average Age (Weeks)', 'Breed', 'Breed Percentage',
            'Daily Egg Production', 'Weekly Egg Production',
            'Small Eggs %', 'Medium Eggs %', 'Large Eggs %',
            'XL Eggs %', 'Jumbo Eggs %', 'Defective Eggs %', 'First Grade Egg %',
            'Avg Feed Consumption', 'Avg Water Intake',
            'Weekly Mortality Rate', 'Total Mortality', 'Hens Culled',
            'Expected Cull Date', 'Recent Placement Date', 'Age at Placement',
            'Upcoming Placement Date', 'Health Issues', 'Recent Vaccinations',
            'Next Vaccination Date', 'Time to Distribution', 'Market Condition Notes',
            'Weekly Production Trend', 'Seasonal Trend Notes'
        ]
        csv_writer.writerow(header)

        for farm in data:
            csv_writer.writerow([
                farm.supplier_name, farm.farm_name, farm.site_name, farm.hen_house_number,
                farm.current_number_of_hens, farm.average_age_weeks, farm.breed, farm.breed_percentage,
                farm.daily_egg_production, farm.weekly_egg_production,
                farm.small_eggs_percentage, farm.medium_eggs_percentage, farm.large_eggs_percentage,
                farm.extra_large_eggs_percentage, farm.jumbo_eggs_percentage, farm.defective_eggs_percentage,
                farm.first_grade_egg_percentage, farm.average_feed_consumption, farm.average_water_intake,
                farm.weekly_mortality_rate, farm.total_mortality, farm.hens_culled,
                farm.expected_cull_date, farm.recent_placement_date, farm.age_of_pullets_at_placement,
                farm.upcoming_placement_date, farm.health_issues, farm.recent_vaccinations,
                farm.next_vaccination_date, farm.time_to_distribution, farm.market_condition_notes,
                farm.weekly_production_trend, farm.seasonal_trend_notes
            ])

        # Add CSV to ZIP
        zip_file.writestr("egg_farms.csv", csv_string_io.getvalue())

        # ====== 2. Create Excel (.xlsx) content ======
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Egg Farms"
        ws.append(header)

        for farm in data:
            ws.append([
                farm.supplier_name, farm.farm_name, farm.site_name, farm.hen_house_number,
                farm.current_number_of_hens, farm.average_age_weeks, farm.breed, farm.breed_percentage,
                farm.daily_egg_production, farm.weekly_egg_production,
                farm.small_eggs_percentage, farm.medium_eggs_percentage, farm.large_eggs_percentage,
                farm.extra_large_eggs_percentage, farm.jumbo_eggs_percentage, farm.defective_eggs_percentage,
                farm.first_grade_egg_percentage, farm.average_feed_consumption, farm.average_water_intake,
                farm.weekly_mortality_rate, farm.total_mortality, farm.hens_culled,
                farm.expected_cull_date, farm.recent_placement_date, farm.age_of_pullets_at_placement,
                farm.upcoming_placement_date, farm.health_issues, farm.recent_vaccinations,
                farm.next_vaccination_date, farm.time_to_distribution, farm.market_condition_notes,
                farm.weekly_production_trend, farm.seasonal_trend_notes
            ])

        # Auto-fit Excel columns
        for col in ws.columns:
            max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max_length + 2

        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        zip_file.writestr("egg_farms.xlsx", excel_buffer.read())

    # Return ZIP Response
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer.read(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="egg_farms_export.zip"'
    return response



@critical_view_decorator
@login_required(login_url='login')
def dashboard_analytics_data(request):
    """
    Provide analytics data for dashboard.
    """
    farm = request.GET.get('farm', None)
    queryset = EggFarm.objects.all()

    if farm:
        queryset = queryset.filter(farm_name__icontains=farm)

    # Feed vs Water
    feed_vs_water = list(queryset.values_list('average_feed_consumption', 'average_water_intake'))

    # Breed Distribution
    breed_counts = queryset.values('breed').annotate(total=Count('id')).order_by('-total')
    breed_distribution = {
        'labels': [b['breed'] for b in breed_counts],
        'data': [b['total'] for b in breed_counts]
    }

    # Mortality and Cull Rate per Breed
    mortality_data = queryset.values('breed').annotate(
        avg_mortality=Avg('weekly_mortality_rate'),
        total_culled=Sum('hens_culled')
    )
    mortality_cull = {
        'labels': [m['breed'] for m in mortality_data],
        'mortality': [round(m['avg_mortality'] or 0, 2) for m in mortality_data],
        'culled': [m['total_culled'] or 0 for m in mortality_data]
    }

    # Egg Quality
    quality = queryset.aggregate(
        defective=Avg('defective_eggs_percentage'),
        first_grade=Avg('first_grade_egg_percentage')
    )
    egg_quality = {
        'defective': round(quality['defective'] or 0, 2),
        'first_grade': round(quality['first_grade'] or 0, 2)
    }

    return JsonResponse({
        'feed_vs_water': feed_vs_water,
        'breed_distribution': breed_distribution,
        'mortality_cull': mortality_cull,
        'egg_quality': egg_quality
    })


@critical_view_decorator
@login_required(login_url='login')
def weekly_production_data(request):
    data = (
        EggFarm.objects
        .annotate(week=TruncWeek('production_date'))
        .values('week')
        .annotate(total_production=Sum('weekly_egg_production'))
        .order_by('week')
    )

    chart_data = {
        'labels': [d['week'].strftime("%Y-%m-%d") for d in data],
        'data': [d['total_production'] for d in data]
    }
    return JsonResponse(chart_data)


from django.http import JsonResponse
from django.db.models import Sum, Avg
from django.db.models.functions import TruncWeek
from .models import EggFarm
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
import pandas as pd
import numpy as np
from datetime import timedelta

def weekly_forecast_data(request):
    farm = request.GET.get('farm')
    site = request.GET.get('site_name')
    breed = request.GET.get('breed')
    health = request.GET.get('health_status')
    range_val = request.GET.get('range', '4')

    try:
        future_weeks = int(range_val.replace('m', '')) * 4 if range_val.endswith('m') else int(range_val.replace('w', ''))
    except ValueError:
        return JsonResponse({'error': 'Invalid range parameter.'}, status=400)

    queryset = EggFarm.objects.all()
    if farm:
        queryset = queryset.filter(farm_name=farm)
    if site:
        queryset = queryset.filter(site_name=site)
    if breed:
        queryset = queryset.filter(breed=breed)
    if health:
        queryset = queryset.filter(health_issues=health)

    data = (
        queryset
        .annotate(week=TruncWeek('production_date'))
        .values('week')
        .annotate(
            total=Sum('weekly_egg_production'),
            avg_production=Avg('weekly_egg_production')
        )
        .order_by('week')
    )

    if not data or len(data) < 2:
        return JsonResponse({
            'labels': [], 
            'actual': [], 
            'forecast': [], 
            'error': 'Insufficient data for forecasting. Need at least 2 weeks of historical data.'
        })

    df = pd.DataFrame(data)
    df.rename(columns={'week': 'ds', 'total': 'y'}, inplace=True)
    df['ds'] = pd.to_datetime(df['ds'])
    df['y'] = df['y'].fillna(df['avg_production'])
    df['x'] = range(len(df))

    try:
        model = make_pipeline(PolynomialFeatures(degree=2), LinearRegression())
        model.fit(df[['x']], df['y'])
        last_date = df['ds'].max()
        future_dates = [last_date + timedelta(weeks=i) for i in range(1, future_weeks + 1)]
        forecast_y = model.predict(np.array(range(len(df), len(df) + future_weeks)).reshape(-1, 1))
    except Exception as e:
        return JsonResponse({
            'labels': [], 
            'actual': [], 
            'forecast': [], 
            'error': f'Forecast calculation error: {str(e)}'
        })

    # Combined timeline
    labels = df['ds'].dt.strftime('%Y-%m-%d').tolist() + [d.strftime('%Y-%m-%d') for d in future_dates]
    
    # Combined actual + forecast line (continuous)
    actual = df['y'].tolist() + forecast_y.round(2).tolist()
    
    # Forecast only line (nulls for past)
    forecast = [None] * len(df) + forecast_y.round(2).tolist()

    return JsonResponse({
        'labels': labels,
        'actual': actual,
        'forecast': forecast
    })

@critical_view_decorator
@login_required(login_url='login')
def dashboard(request):
    """
    Render the working dashboard page with summarized stats and filters.
    """
    egg_farms = EggFarm.objects.all()

    # Filters
    farm = request.GET.get('farm')
    site_name = request.GET.get('site_name')
    breed = request.GET.get('breed')
    min_hens = request.GET.get('min_hens')
    max_hens = request.GET.get('max_hens')
    health_status = request.GET.get('health_status')
    min_age = request.GET.get('min_age')
    max_age = request.GET.get('max_age')

    if farm:
        egg_farms = egg_farms.filter(farm_name__icontains=farm)
    if site_name:
        egg_farms = egg_farms.filter(site_name__icontains=site_name)
    if breed:
        egg_farms = egg_farms.filter(breed=breed)
    if min_hens:
        egg_farms = egg_farms.filter(current_number_of_hens__gte=int(min_hens))
    if max_hens:
        egg_farms = egg_farms.filter(current_number_of_hens__lte=int(max_hens))
    if health_status:
        egg_farms = egg_farms.filter(health_issues=health_status)
    if min_age:
        egg_farms = egg_farms.filter(average_age_weeks__gte=float(min_age))
    if max_age:
        egg_farms = egg_farms.filter(average_age_weeks__lte=float(max_age))

    total_farms = egg_farms.values('farm_name').distinct().count()
    total_hens = egg_farms.aggregate(Sum('current_number_of_hens'))['current_number_of_hens__sum'] or 0
    average_age = egg_farms.aggregate(Avg('average_age_weeks'))['average_age_weeks__avg'] or 0
    total_weekly_production = egg_farms.aggregate(Sum('weekly_egg_production'))['weekly_egg_production__sum'] or 0

    egg_size_distribution = {
        'small': egg_farms.aggregate(Sum('small_eggs_percentage'))['small_eggs_percentage__sum'] or 0,
        'medium': egg_farms.aggregate(Sum('medium_eggs_percentage'))['medium_eggs_percentage__sum'] or 0,
        'large': egg_farms.aggregate(Sum('large_eggs_percentage'))['large_eggs_percentage__sum'] or 0,
        'extra_large': egg_farms.aggregate(Sum('extra_large_eggs_percentage'))['extra_large_eggs_percentage__sum'] or 0,
        'jumbo': egg_farms.aggregate(Sum('jumbo_eggs_percentage'))['jumbo_eggs_percentage__sum'] or 0,
    }

    context = {
        'total_farms': total_farms,
        'total_hens': total_hens,
        'average_age': round(average_age, 1),
        'total_weekly_production': total_weekly_production,
        'egg_size_distribution': egg_size_distribution,
        'farm_names': EggFarm.objects.values_list('farm_name', flat=True).distinct().order_by('farm_name'),
        'site_names': EggFarm.objects.values_list('site_name', flat=True).distinct().order_by('site_name'),
        'breed_choices': EggFarm.BREED_CHOICES,
        'health_choices': EggFarm.HEALTH_CHOICES,
    }

    return render(request, 'main/dashboard.html', context)




@critical_view_decorator
@login_required(login_url='login')
def farm_autocomplete(request):
    """
    Provide autocomplete suggestions for farm names.
    """
    term = request.GET.get('term', '')
    farms = EggFarm.objects.filter(
        farm_name__icontains=term
    ).values_list('farm_name', flat=True).distinct()
    
    suggestions = [{'id': farm, 'text': farm} for farm in farms if farm]

    return JsonResponse(suggestions, safe=False)

@critical_view_decorator
@login_required(login_url='login')
def clear_database(request):
    """
    Clear all egg farm records from the database.
    Requires user authentication.
    """
    if request.method == 'POST':
        with transaction.atomic():
            EggFarm.objects.all().delete()
            messages.success(request, "All egg farm records have been successfully deleted.")
        return redirect('egg_farm_list')
    else:
        messages.error(request, "Invalid request method.")
        return redirect('egg_farm_list')

# Authentication Views
@csrf_protect
def register_user(request):
    """
    Handle user registration with enhanced security.
    """
    # Force logout of any existing session
    if request.user.is_authenticated:
        logout(request)
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            # Create user with additional security steps
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}. You can now log in.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})



@never_cache
@csrf_protect
def login_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('home')  # Go to home/dashboard
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'accounts/login.html')





def logout_user(request):
    logout(request)
    return redirect('login')
    """
    Handle user logout with enhanced security.
    """
    # Clear all messages
    storage = messages.get_messages(request)
    storage.used = True
    
    # Completely invalidate the session
    request.session.flush()
    
    # Logout and redirect
    logout(request)
    
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


# View all users
@login_required(login_url='login')
def user_list(request):
    users = User.objects.all()
    return render(request, 'accounts/user_list.html', {'users': users})

# Edit user password
@login_required(login_url='login')
def edit_user_password(request, user_id):
    user = get_object_or_404(User, id=user_id)
    form = SetPasswordForm(user, request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Password updated successfully.')
            return redirect('user_list')
        else:
            messages.error(request, 'Please correct the errors below.')

    return render(request, 'accounts/edit_password.html', {'form': form, 'user_obj': user})

# Delete user
@login_required(login_url='login')
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('user_list')
    return render(request, 'accounts/confirm_delete.html', {'user_obj': user})


@login_required(login_url='login')
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        # You can add a form to edit the user fields like username, email, etc.
        form = UserForm(request.POST, instance=user)  # Assuming `UserForm` is the form to edit user fields.
        if form.is_valid():
            form.save()
            messages.success(request, 'User details updated successfully!')
            return redirect('user_list')
    else:
        form = UserForm(instance=user)
    
    return render(request, 'accounts/edit_user.html', {'form': form, 'user': user})





def validate_egg_farm_data(row):
    """
    Validate and clean imported data row.
    Returns a cleaned dictionary or None if invalid.
    """
    try:
        return {
            'supplier_name': str(row[0]).strip(),
            'farm_name': str(row[1]).strip(),
            'site_name': str(row[2]).strip(),
            'hen_house_number': str(row[3]).strip(),
            'current_number_of_hens': int(row[4]),
            'average_age_weeks': float(row[5]),
            'breed': str(row[6]).strip(),
            'breed_percentage': float(row[7]),
            'daily_egg_production': float(row[8]),
            'weekly_egg_production': float(row[9]),
            'small_eggs_percentage': float(row[10]),
            'medium_eggs_percentage': float(row[11]),
            'large_eggs_percentage': float(row[12]),
            'extra_large_eggs_percentage': float(row[13]),
            'jumbo_eggs_percentage': float(row[14]),
            'defective_eggs_percentage': float(row[15]),
            'first_grade_egg_percentage': float(row[16]),
            'average_feed_consumption': float(row[17]),
            'average_water_intake': float(row[18]),
            'weekly_mortality_rate': float(row[19]),
            'total_mortality': int(row[20]),
            'hens_culled': int(row[21]),
            'expected_cull_date': parse_date(row[22]),
            'recent_placement_date': parse_date(row[23]),
            'age_of_pullets_at_placement': float(row[24]),
            'upcoming_placement_date': parse_date(row[25]),
            'health_issues': str(row[26]).strip(),
            'recent_vaccinations': str(row[27]).strip(),
            'next_vaccination_date': parse_date(row[28]),
            'time_to_distribution': int(row[29]),
            'market_condition_notes': str(row[30]).strip(),
            'weekly_production_trend': float(row[31]),
            'seasonal_trend_notes': str(row[32]).strip(),
            'production_date': parse_date(row[33])  # ✅ Added production_date here
        }
    except Exception as e:
        print(f"⚠️ Row validation exception: {e}")
        return None




def create_user(request):
    """
    View to create a new user.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'User created successfully.')
            return redirect('user_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreationForm()

    return render(request, 'accounts/create_user.html', {'form': form})