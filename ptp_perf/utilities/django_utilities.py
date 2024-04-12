import logging
import os

from django.db import connection


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
