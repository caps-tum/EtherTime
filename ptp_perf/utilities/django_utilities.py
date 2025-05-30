import logging
import os
from typing import Callable

from admin_actions.admin import ActionsModelAdmin
from django.core.exceptions import FieldDoesNotExist
from django.db import connection, models

from ptp_perf.utilities import units


def bootstrap_django_environment():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ptp_perf.django_data.site.settings')

    try:
        from django.core.wsgi import get_wsgi_application
        get_wsgi_application()
    except ImportError as e:
        logging.error(f"Failed to import django settings: {e}")
        raise


def get_server_datetime():
    """Function to query the current time from the database because we often have no idea what time it is."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT NOW()")
        return cursor.fetchone()[0]


def create_format_function(field: models.FloatField, format_function: Callable[[float], str]) -> Callable:
    def inner(obj) -> str:
        return format_function(obj.__dict__[field.db_column])

    inner.admin_order_field = field.db_column
    inner.short_description = field.name
    return inner


class FormattedFloatField(models.FloatField):
    format_function: Callable[[float], str] = lambda x: str(x)

class TimeFormatFloatField(FormattedFloatField):
    format_function = lambda x: units.format_time_offset(x, auto_increase_places=True)

class DataFormatFloatField(FormattedFloatField):
    format_function = lambda x: units.format_engineering(x, unit='B')

class GenericEngineeringFloatField(FormattedFloatField):
    format_function = lambda x: units.format_engineering(x, unit='')


class PercentageFloatField(FormattedFloatField):
    format_function = lambda x: units.format_percentage(x)

class TemperatureFormatFloatField(FormattedFloatField):
    format_function = lambda x: f"{x:.1f}°C"

class FrequencyFormatFloatField(FormattedFloatField):
    format_function = lambda x: f"{x:.0f}MHz"


class CustomFormatsAdmin(ActionsModelAdmin):
    def __new__(cls, model, admin_site):
        for field in model._meta.fields:
            if isinstance(field, FormattedFloatField):
                cls.add_custom_float_display_method(model, field)
        return super().__new__(cls)

    @staticmethod
    def add_custom_float_display_method(model, field: FormattedFloatField):
        def custom_float_display(obj):
            format_function = field.__class__.format_function
            value = getattr(obj, field.name)
            if value is None:
                return "-"
            return format_function(value)

        custom_float_display.short_description = field.verbose_name
        custom_float_display.admin_order_field = field.name  # Add admin_order_field
        custom_float_display.__name__ = f'custom_{field.name}_display'
        setattr(model, custom_float_display.__name__, custom_float_display)

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        custom_list_display = []
        for field_name in list_display:
            try:
                field = self.model._meta.get_field(field_name)
                if isinstance(field, FormattedFloatField):
                    custom_list_display.append(f'custom_{field_name}_display')
                else:
                    custom_list_display.append(field_name)
            except FieldDoesNotExist:
                custom_list_display.append(field_name)
        return custom_list_display


def format_custom_field(instance, field_name: str) -> str:
    field = instance._meta.get_field(field_name)
    value = getattr(instance, field_name)
    if value is None:
        return "-"
    if isinstance(field, FormattedFloatField):
        function = field.__class__.format_function
        return function(value)
    return str(value)
