import argparse
import logging
from argparse import ArgumentParser

from django.core.management import BaseCommand

from ptp_perf import config, util
from ptp_perf.adapters.device_control import DeviceControl
from ptp_perf.util import setup_logging


class Command(BaseCommand):
    help = "Control a device via the smart PDU"

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            "--machine", type=str, required=True,
            choices=config.machines.keys(), help="Device id of the machine to target"
        )
        parser.add_argument(
            "--power", action=argparse.BooleanOptionalAction, required=True, help="Whether to turn the device on or off"
        )

    def handle(self, *args, **options):
        setup_logging(level=logging.DEBUG)
        with util.StackTraceGuard():
            device_control = DeviceControl(None, None)
            device_control.toggle_machine(config.machines[options["machine"]], options["power"])
