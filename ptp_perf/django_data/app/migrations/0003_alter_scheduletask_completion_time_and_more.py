# Generated by Django 5.0.2 on 2024-04-02 18:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_scheduletask_alter_logrecord_table_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scheduletask',
            name='completion_time',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='scheduletask',
            name='start_time',
            field=models.DateTimeField(null=True),
        ),
    ]
