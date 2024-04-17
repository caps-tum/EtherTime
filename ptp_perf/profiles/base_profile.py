from ptp_perf.profiles.taxonomy import ResourceContentionType, ResourceContentionComponent


class ProfileType:
    RAW = "raw"
    PROCESSED = "processed"
    PROCESSED_CORRUPT = "processed-corrupt"
    AGGREGATED = "aggregated"

class ProfileTags:
    # Load
    CATEGORY_CONFIGURATION = "category_configuration"
    CATEGORY_FAULT = "category_fault"
    CATEGORY_LOAD = "category_load"

    # Component
    COMPONENT_CPU = ResourceContentionComponent.CPU.tag
    COMPONENT_NET = ResourceContentionComponent.NET.tag
    COMPONENT_AUX = ResourceContentionComponent.AUX.tag

    # Isolation
    ISOLATION_UNPRIORITIZED = ResourceContentionType.UNPRIORITIZED.tag
    ISOLATION_PRIORITIZED = ResourceContentionType.PRIORITIZED.tag
    ISOLATION_ISOLATED = ResourceContentionType.ISOLATED.tag

    # Fault types
    FAULT_SOFTWARE = "fault_software"
    FAULT_HARDWARE = "fault_hardware"

    # Fault locations
    FAULT_LOCATION_SWITCH = "fault_location_switch"
    FAULT_LOCATION_SLAVE = "fault_location_slave"
    FAULT_LOCATION_MASTER = "fault_location_master"

    # Configuration Settings
    CONFIGURATION_INTERVAL = "configuration_interval"
