from typing import Dict, List

from registry.base_registry import BaseRegistry
from vendor.linuxptp import LinuxPTPVendor
from vendor.ptpd import PTPDVendor
from vendor.systemd_ntp import SystemDNTPVendor
from vendor.vendor import Vendor


class VendorDB(BaseRegistry):
    """Singleton class holding all registered vendors"""

    SYSTEMD_NTP = SystemDNTPVendor()
    PTPD = PTPDVendor()
    LINUXPTP = LinuxPTPVendor()

    ANALYZED_VENDORS: List[Vendor] = [PTPD, LINUXPTP]


VendorDB.register_all(
    VendorDB.SYSTEMD_NTP,
    VendorDB.PTPD,
    VendorDB.LINUXPTP,
)
