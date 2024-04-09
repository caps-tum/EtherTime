from typing import Dict, List

from ptp_perf.registry.base_registry import BaseRegistry
from ptp_perf.vendor.linuxptp import LinuxPTPVendor
from ptp_perf.vendor.ptpd import PTPDVendor
from ptp_perf.vendor.sptp import SPTPVendor
from ptp_perf.vendor.systemd_ntp import SystemDNTPVendor
from ptp_perf.vendor.vendor import Vendor


class VendorDB(BaseRegistry):
    """Singleton class holding all registered vendors"""

    SYSTEMD_NTP = SystemDNTPVendor()
    PTPD = PTPDVendor()
    LINUXPTP = LinuxPTPVendor()
    SPTP = SPTPVendor()

    ANALYZED_VENDORS: List[Vendor] = [PTPD, LINUXPTP, SPTP]


VendorDB.register_all(
    VendorDB.SYSTEMD_NTP,
    VendorDB.PTPD,
    VendorDB.LINUXPTP,
    VendorDB.SPTP,
)
