from django.db import models


class EndpointType(models.TextChoices):
    UNKNOWN = 'UNKNOWN'
    MASTER = 'MASTER'
    PRIMARY_SLAVE = 'PRIMARY_SLAVE'
    SECONDARY_SLAVE = 'SECONDARY_SLAVE'
    TERTIARY_SLAVE = 'TERTIARY_SLAVE'
    ORCHESTRATOR = 'ORCHESTRATOR'
    SWITCH = "SWITCH"

    # Special value that should match any slave, it should not be directly assigned to endpoints
    SPECIAL_SLAVE_ANY = "SLAVE_ANY"
