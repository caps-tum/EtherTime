# from datetime import timedelta
# from typing import Optional
#
# from django.db import models
#
# import constants
# from ptp_perf.constants import DEFAULT_BENCHMARK_DURATION
# from models.tag import Tag
#
#
# class Benchmark(models.Model):
#     id = models.CharField(primary_key=True)
#     name = models.CharField(unique=True)
#     tags = models.ManyToManyField(Tag)
#     version = models.IntegerField(default=1)
#     duration = models.DurationField(default=DEFAULT_BENCHMARK_DURATION)
#     num_machines = models.IntegerField(default=2)
#
#     class PTPDelayMechanism(models.TextChoices):
#         END_TO_END = "E2E"
#         PEER_TO_PEER = "P2P"
#
#     ptp_delay_mechanism = models.CharField(choices=PTPDelayMechanism, default=PTPDelayMechanism.END_TO_END)
#     log_announce_interval = models.IntegerField(default=1)
#     log_sync_interval = models.IntegerField(default=0)
#     log_delayreq_interval = models.IntegerField(default=0)
#
#
#     ptp_keepalive = models.BooleanField(default=False)
#     ptp_restart_delay = models.DurationField(null=True, default=None)
#
#     artificial_load_network: Optional[int] = models.IntegerField(null=True, default=None)
#     artificial_load_network_dscp_priority: Optional[str] = models.IntegerField(null=True, default=None)
#     artificial_load_network_secondary_interface: Optional[bool] = models.BooleanField(null=True, default=None)
#
#     artificial_load_cpu: Optional[int] = models.IntegerField(null=True, default=None)
#     artificial_load_cpu_scheduler: Optional[str] = models.CharField(null=True, default=None)
#     artificial_load_cpu_restrict_cores: Optional[bool] = models.BooleanField(null=True, default=None)
#
#
#     class FaultToleranceType(models.TextChoices):
#         SOFTWARE = "software"
#         HARDWARE = "hardware"
#
#     fault_tolerance_fault_type = models.CharField(choices=FaultToleranceType.choices, null=True, default=None)
#     fault_tolerance_fault_interval = models.DurationField(null=True, default=None)
#     fault_tolerance_fault_machine = models.ForeignKey()
#
#     @property
#     def storage_base_path(self):
#         return constants.MEASUREMENTS_DIR.joinpath(self.id)
