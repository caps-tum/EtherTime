from django.db import models


class EndpointType(models.TextChoices):
    UNKNOWN = 'UNKNOWN'
    MASTER = 'MASTER'
    PRIMARY_SLAVE = 'PRIMARY_SLAVE'
    SECONDARY_SLAVE = 'SECONDARY_SLAVE'
    ORCHESTRATOR = 'ORCHESTRATOR'
    SWITCH = "SWITCH"
