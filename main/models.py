from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class EggFarm(models.Model):
    # Farm Identification
    supplier_name = models.CharField(max_length=200)
    farm_name = models.CharField(max_length=200)
    site_name = models.CharField(max_length=200)
    hen_house_number = models.CharField(max_length=50)

    # Hen Population and Breed
    BREED_CHOICES = [
        ('LEGHORN', 'Leghorn'),
        ('RHODE_ISLAND_RED', 'Rhode Island Red'),
        ('PLYMOUTH_ROCK', 'Plymouth Rock'),
        ('AUSTRALORP', 'Australorp'),
        ('ORPINGTON', 'Orpington'),
        ('OTHER', 'Other')
    ]

    current_number_of_hens = models.PositiveIntegerField()
    average_age_weeks = models.FloatField()
    breed = models.CharField(max_length=50, choices=BREED_CHOICES)
    breed_percentage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Egg Production
    daily_egg_production = models.FloatField(help_text="Daily egg production in dozens")
    weekly_egg_production = models.FloatField(help_text="Weekly egg production in dozens")

    # Egg Size Distribution
    small_eggs_percentage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    medium_eggs_percentage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    large_eggs_percentage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    extra_large_eggs_percentage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    jumbo_eggs_percentage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Egg Quality
    defective_eggs_percentage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    first_grade_egg_percentage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Nutrition and Consumption
    average_feed_consumption = models.FloatField(help_text="Average feed consumption in g/hen/day")
    average_water_intake = models.FloatField(help_text="Average water intake in L/hen/day")

    # Mortality and Culling
    weekly_mortality_rate = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    total_mortality = models.PositiveIntegerField()
    hens_culled = models.PositiveIntegerField()
    expected_cull_date = models.DateField(null=True, blank=True)

    # Placement and Age
    recent_placement_date = models.DateField(null=True, blank=True)
    age_of_pullets_at_placement = models.FloatField(null=True, blank=True)
    upcoming_placement_date = models.DateField(null=True, blank=True)

    # Health Management
    HEALTH_CHOICES = [
        ('Y', 'Yes'),
        ('N', 'No')
    ]
    health_issues = models.CharField(max_length=1, choices=HEALTH_CHOICES)
    recent_vaccinations = models.TextField(null=True, blank=True)
    next_vaccination_date = models.DateField(null=True, blank=True)

    # Distribution and Market
    time_to_distribution = models.PositiveIntegerField(
        help_text="Time from egg collection to distribution (days)"
    )
    market_condition_notes = models.TextField(null=True, blank=True)

    # Production Trends
    weekly_production_trend = models.FloatField(
        help_text="Weekly production trend (%) compared to last week"
    )
    seasonal_trend_notes = models.TextField(null=True, blank=True)

    # Production Date (IMPORTANT field for forecast)
    production_date = models.DateField(help_text="Date representing the week of production", null=True, blank=True)

    # Timestamp for record keeping
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.farm_name} - {self.site_name} - House {self.hen_house_number} ({self.production_date})"

    class Meta:
        verbose_name = "Egg Farm Record"
        verbose_name_plural = "Egg Farm Records"
        # MODIFIED: Include production_date in unique_together
        unique_together = ['farm_name', 'site_name', 'hen_house_number', 'production_date']
        # Add index for faster querying
        indexes = [
            models.Index(fields=['production_date']),
            models.Index(fields=['farm_name', 'site_name', 'hen_house_number']),
        ]