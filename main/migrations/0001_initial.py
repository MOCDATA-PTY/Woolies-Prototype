# Generated by Django 5.1.7 on 2025-03-16 14:49

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Shipment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Claim_No', models.CharField(max_length=100, unique=True)),
                ('Claiming_Client', models.CharField(blank=True, max_length=100, null=True)),
                ('Branch', models.CharField(choices=[('ATL', 'ATL'), ('CMU', 'CMU'), ('CON', 'CON'), ('DOR', 'DOR'), ('HEC', 'HEC'), ('HNL', 'HNL'), ('HOU', 'HOU'), ('ICS', 'ICS'), ('IMP', 'IMP'), ('JFK', 'JFK'), ('LAX', 'LAX'), ('LCL', 'LCL'), ('ORD', 'ORD'), ('PPG', 'PPG')], max_length=3)),
                ('Formal_Claim_Received', models.CharField(blank=True, choices=[('YES', 'Yes'), ('NO', 'No')], max_length=3, null=True)),
                ('Intend_Claim_Date', models.DateField(blank=True, null=True)),
                ('Formal_Claim_Date_Received', models.DateField(blank=True, null=True)),
                ('Claimed_Amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('Closed_Date', models.DateField(blank=True, null=True)),
                ('Amount_Paid_By_Carrier', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('Amount_Paid_By_Awa', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('Amount_Paid_By_Insurance', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
            ],
        ),
    ]
