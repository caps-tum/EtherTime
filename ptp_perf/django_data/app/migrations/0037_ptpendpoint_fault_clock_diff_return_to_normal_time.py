# Generated by Django 5.0.2 on 2024-05-15 23:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0036_ptpendpoint_converged_percentage_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='ptpendpoint',
            name='fault_clock_diff_return_to_normal_time',
            field=models.DurationField(null=True),
        ),
    ]
