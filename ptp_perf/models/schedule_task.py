import asyncio
import logging
from datetime import timedelta, datetime
from typing import Optional

from django.db import models
from django.utils import timezone

from ptp_perf.invoke.invocation import Invocation, InvocationFailedException


class ScheduleTask(models.Model):
    id: int = models.AutoField(primary_key=True)
    priority: int = models.IntegerField(default=0)
    name: str = models.CharField(max_length=255)
    command: str = models.TextField()
    paused: bool = models.BooleanField(default=False)
    estimated_time: timedelta = models.DurationField()
    slack_time: timedelta = models.DurationField(default=timedelta(minutes=5))

    success: Optional[bool] = models.BooleanField(null=True, blank=True)
    start_time: Optional[datetime] = models.DateTimeField(null=True, blank=True)
    completion_time: Optional[datetime] = models.DateTimeField(null=True, blank=True)

    def run(self):
        self.start_time = timezone.now()
        self.priority = 999
        self.save()
        try:
            invocation = Invocation.of_shell(command=self.command)
            asyncio.run(invocation.run(timeout=self.timeout.total_seconds()))
            self.success = True
        except InvocationFailedException as e:
            logging.warning(f"Failed to run task: {e}")
            self.success = False
        self.completion_time = timezone.now()
        logging.info(f"Task {self.id} completed at {self.completion_time} (success: {self.success}).")

        self.save()

    @property
    def completed(self):
        return self.success is not None

    @property
    def estimated_time_remaining(self) -> timedelta:
        """Estimated task time remaining, based off of whether the task is started."""
        if not self.running:
            return self.estimated_time

        return max(timedelta(minutes=0), self.estimated_time - (timezone.now() - self.start_time))

    @property
    def running(self) -> bool:
        return self.start_time is not None

    @property
    def timeout(self):
        if self.estimated_time is None or self.slack_time is None:
            return None
        return self.estimated_time + self.slack_time

    def __str__(self):
        return f"{self.name} ({self.id if self.id is not None else 'new'})"

    class Meta:
        app_label = 'app'
        ordering = ('-completion_time', '-priority', 'id',)
