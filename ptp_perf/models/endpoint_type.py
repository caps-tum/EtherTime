from django.db import models


class EndpointType(models.TextChoices):
    """The role of a worker in the cluster. This is used to determine the PTP configuration for the worker."""
    UNKNOWN = 'UNKNOWN'
    MASTER = 'MASTER'
    """The primary master of the PTP cluster."""
    PRIMARY_SLAVE = 'PRIMARY_SLAVE'
    """A primary slave of the PTP cluster. This is the slave that is principally used to collect statistics."""
    SECONDARY_SLAVE = 'SECONDARY_SLAVE'
    """A secondary slave of the PTP cluster. This is the slave that is used as a failover master for the failover benchmark or as a comparison for the primary master during regular fault benchmarks."""
    TERTIARY_SLAVE = 'TERTIARY_SLAVE'
    """All other slaves in the cluster, used for scalability benchmarks."""
    ORCHESTRATOR = 'ORCHESTRATOR'
    """The orchestrator machine that runs the PTP-Perf benchmarking suite."""
    SWITCH = "SWITCH"
    """Network hardware that can be powered on or off via smart PDUs in the network fault switch benchmark."""

    # Special value that should match any slave, it should not be directly assigned to endpoints
    SPECIAL_SLAVE_ANY = "SLAVE_ANY"
    """A special value that matches any slaved. It should not be directly assigned to endpoints, it is used for filtering and querying purposes."""