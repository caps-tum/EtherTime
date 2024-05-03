import logging

from django.db import models


class LogLevel(models.IntegerChoices):
    """Represent python logging levels in the database as an integer."""
    DEBUG = logging.DEBUG, 'Debug'
    INFO = logging.INFO, 'Info'
    WARNING = logging.WARNING, 'Warning'
    ERROR = logging.ERROR, 'Error'
    CRITICAL = logging.CRITICAL, 'Critical'
