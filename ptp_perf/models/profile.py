from typing import Any

from django.db import models


class PTPProfile(models.Model):
    id = models.AutoField(primary_key=True)
    benchmark = models.CharField(max_length=255, null=False, blank=False)
    vendor_id: models.CharField(max_length=255, null=False, blank=False)

    class PTPProfileState(models.TextChoices):
        VALID = "valid"

    state = models.CharField(choices=PTPProfileState, max_length=255)

    start_time = models.DateTimeField()
    stop_time = models.DateTimeField()

