import json
import logging

import psutil

from ptp_perf.adapters.adapter import IntervalActionAdapter
from ptp_perf.util import unpack_one_value
from ptp_perf.utilities import psutil_utilities


class ResourceMonitor(IntervalActionAdapter):
    log_source = 'resource_monitor'

    async def update(self):
        system_data = {
            'cpu_times': psutil.cpu_times(),
            'cpu_percent': psutil.cpu_percent(),
            'cpu_stats': psutil.cpu_stats(),
            'cpu_freq': psutil.cpu_freq(),
            'virtual_memory': psutil.virtual_memory(),
            'disk_io_counters': psutil.disk_io_counters(),
            'net_io_counters': psutil.net_io_counters(pernic=True),
            'sensors_temperature': psutil.sensors_temperatures(),
        }

        process_data = {}
        invocation = unpack_one_value(self.endpoint.profile.vendor.get_processes())
        if invocation is not None and invocation._process is not None:
            pid = invocation._process.pid
            try:
                process = psutil.Process(pid)
                process_data = process.as_dict(
                    ["cpu_times", "cpu_percent", 'io_counters', 'memory_full_info', 'num_ctx_switches', 'num_threads']
                )
            except psutil.NoSuchProcess:
                logging.info(f"Resource monitor: Process {pid} not found.")

        all_data = {
            'system': system_data,
            'process': process_data,
        }

        all_data = psutil_utilities.recursive_namedtuple_to_dict(all_data)
        self.log(json.dumps(all_data))
