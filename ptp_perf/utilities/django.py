import os


def bootstrap_django_environment():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ptp_perf.django.site.settings')
    from django.core.wsgi import get_wsgi_application
    get_wsgi_application()
