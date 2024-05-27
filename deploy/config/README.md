# PTP Configurations

This folder contains the default configurations for the Precision Time Protocol (PTP) software packages used in the EtherTime project. The configurations are designed to work with the `ptpd`, `linuxptp`, `sptp` and `chrony` packages, which are used to synchronize the clocks of the EtherTime nodes.

The default configuration is provided for reference, from which we derive a master and slave configuration for each package. These are formatted as Jinja2 templates, which are used to generate the final configuration files from the machine's PTPConfig for each node during each benchmark.
