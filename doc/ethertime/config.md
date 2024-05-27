# Getting Started with Customizing the EtherTime Configuration

The `config.py` file in the `ptp_perf` directory is where you define the machines and clusters for your EtherTime project. This guide will walk you through the process of customizing this configuration.

## 1. Understanding the Configuration

The configuration is defined using Python dataclasses. Each machine is represented by an instance of the `Machine` class, and each cluster is represented by an instance of the `Cluster` class.

A machine has several properties, including its ID, address, PTP address, endpoint type, PTP interface, and other settings. A cluster is simply a collection of machines.

Refer to inline comments in `config.py` for details on the default configuration.

## 2. Defining a Machine

To define a new machine, create a new instance of the `Machine` class. Here's an example:

```python
MACHINE_NEW = Machine(
    id="new", address="new", remote_root="/home/new/ptp-perf",
    ptp_address="10.0.0.10",
    endpoint_type=EndpointType.MASTER,
    ptp_interface='eth0',
    ptp_use_phc2sys=False,
    ptp_software_timestamping=True,
    python_executable='python3.11',
    shutdown_delay=timedelta(minutes=1),
    plugin_settings=PluginSettings(
        iperf_server=True, iperf_address="10.0.0.10", iperf_secondary_address="192.168.1.10",
        stress_ng_cpus=4, stress_ng_cpu_restrict_cores="2,3")
)
```

Replace the values with your own. The `id` and `address` should be unique for each machine. The `remote_root` is the directory on the machine where the EtherTime project will be stored. The `ptp_address` is the IP address of the machine on the PTP network.

The `endpoint_type` determines the role of the machine in the PTP network. It can be `EndpointType.MASTER`, `EndpointType.PRIMARY_SLAVE`, `EndpointType.SECONDARY_SLAVE`, `EndpointType.TERTIARY_SLAVE`, or `EndpointType.ORCHESTRATOR`.

The `ptp_interface` is the network interface used for PTP. The `ptp_use_phc2sys` and `ptp_software_timestamping` settings control the PTP configuration.

The `python_executable` is the path to the Python interpreter that will be used to run the EtherTime project on the machine.

The `plugin_settings` control the settings for the iperf and stress-ng plugins.

For details on the available settings, refer to the `Machine` class in `machine.py`.

## 3. Defining a Cluster

To define a new cluster, create a new instance of the `Cluster` class. Here's an example:

```python
CLUSTER_NEW = Cluster(
    id="new",
    name="New Cluster",
    machines=[
        MACHINE_NEW
    ]
)
```

Replace the values with your own. The `id` should be unique for each cluster. The `name` is a human-readable name for the cluster. The `machines` is a list of `Machine` instances that belong to the cluster.

## 4. Adding the New Configuration

Finally, add the new machine and cluster to the `machines` and `clusters` dictionaries, respectively:

```python
machines = {
    machine.id: machine for machine in [
        MACHINE_NEW,
        # other machines...
    ]
}

clusters = {
    cluster.id: cluster for cluster in [
        CLUSTER_NEW,
        # other clusters...
    ]
}
```

Now, your new machine and cluster are part of the EtherTime configuration. 

That's it! You've successfully customized the configuration in `config.py`.