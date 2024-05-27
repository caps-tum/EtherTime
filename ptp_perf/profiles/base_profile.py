from ptp_perf.profiles.taxonomy import ResourceContentionType, ResourceContentionComponent


class ProfileTags:
    """
    Tags used to categorize and describe profiles.
    They can be attached to benchmarks to describe the type of performance test that is being conducted.
    This allows for easy filtering and searching of profiles.
    """

    # Categories
    # These tags are used to categorize the type of performance test that is being conducted.
    CATEGORY_DEFAULT = "category_default"
    CATEGORY_CONFIGURATION = "category_configuration"
    CATEGORY_FAULT = "category_fault"
    CATEGORY_LOAD = "category_load"
    CATEGORY_RESOURCE_CONSUMPTION = "category_resource_consumption"
    CATEGORY_SCALABILITY = "category_scalability"

    # Component
    # These tags are used to categorize the component of the system that is being loaded for resource contention benchmarks.
    COMPONENT_CPU = ResourceContentionComponent.CPU.tag
    COMPONENT_NET = ResourceContentionComponent.NET.tag
    COMPONENT_AUX = ResourceContentionComponent.AUX.tag

    # Isolation
    # These tags are used to categorize the type of isolation that is being tested for resource contention benchmarks.
    # Unprioritized means that PTP is not prioritized over the generated additional load, leading to contention.
    # Prioritized means that PTP is prioritized over the generated additional load, which should protect against contention.
    # Isolated means that PTP is physically separated from the additional load generated, which should eliminate contention.
    ISOLATION_UNPRIORITIZED = ResourceContentionType.UNPRIORITIZED.tag
    ISOLATION_PRIORITIZED = ResourceContentionType.PRIORITIZED.tag
    ISOLATION_ISOLATED = ResourceContentionType.ISOLATED.tag

    # Fault types
    # These tags are used to categorize the type of fault that is being tested for fault tolerance benchmarks.
    # Fault software means that a software fault is being injected into the system by killing the PTP process.
    # Fault hardware means that a hardware fault is being injected into the system via smart PDU power cycling.
    FAULT_SOFTWARE = "fault_software"
    FAULT_HARDWARE = "fault_hardware"

    # Fault locations
    # These tags are used to categorize the location of the fault that is being tested for fault tolerance benchmarks.
    # Fault location switch means that the fault is being injected into the network switch.
    FAULT_LOCATION_SWITCH = "fault_location_switch"
    FAULT_LOCATION_SLAVE = "fault_location_slave"
    FAULT_LOCATION_MASTER = "fault_location_master"

    # Configuration Settings
    # These tags are used to categorize the PTP configuration settings that are being tested for configuration benchmarks.
    # Configuration interval means that the PTP message interval is being tested.
    CONFIGURATION_INTERVAL = "configuration_interval"
