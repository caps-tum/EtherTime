from typing import Dict

from registry.base_registry import BaseRegistry
from vendor.linuxptp import LinuxPTPVendor
from vendor.ptpd.vendor import PTPDVendor
from vendor.systemd_ntp import SystemDNTPVendor
from vendor.vendor import Vendor


class VendorDB(BaseRegistry):
    """Singleton class holding all registered vendors"""

    SYSTEMD_NTP = SystemDNTPVendor()
    PTPD = PTPDVendor()
    LINUXPTP = LinuxPTPVendor()


VendorDB.register_all(
    VendorDB.SYSTEMD_NTP,
    VendorDB.PTPD,
    VendorDB.LINUXPTP,
)
