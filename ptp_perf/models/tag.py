from django.db import models


class Tag(models.Model):
    id = models.CharField(primary_key=True, max_length=255)

    class TagCategory(models.TextChoices):
        BENCHMARK = 'benchmark'
        MACHINE = 'machine'

    category = models.CharField(choices=TagCategory, max_length=255, null=False, blank=False)


    class Meta:
        app_label = 'app'
