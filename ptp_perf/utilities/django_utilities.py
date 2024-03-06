import logging
import os


def bootstrap_django_environment():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ptp_perf.django_data.site.settings')

    try:
        from django.core.wsgi import get_wsgi_application
        get_wsgi_application()
    except ImportError:
        logging.info("Failed to import django settings")