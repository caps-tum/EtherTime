![EtherTime](doc/project/res/logo_nobg.svg)
# EtherTime: Precision Time Synchronization Evaluation Tools
![Static Badge](https://img.shields.io/badge/Database%20-%20operational%20-%20green)
![Static Badge](https://img.shields.io/badge/Profiles%20collected%20-%201890%20-%20blue)
![Static Badge](https://img.shields.io/badge/Log%20Records%20-%2013M%20-%20blue)

### Overview

EtherTime is an open-source benchmarking tool developed to evaluate the performance of various time synchronization protocols on Ethernet-based distributed systems. This tool is designed to assess the strengths and weaknesses of the supported implementations in different configurations, focusing on dependability and fault tolerance.

### Key Features

- **Cross-Vendor Evaluation**: ⌚⏰⏱⏲ Supports fair and comparable evaluation of four implementations of time synchronization protocols.
- **Distributed Testbeds**: 🖥💻 Orchestrates diverse testbeds fully automatically via SSH and Python, proven to work with Raspberry Pi, Xilinx AVNet, and NVIDIA Jetson embedded boards.
- **Automatic Resource Contention and Fault Injection**:📶⚡ Evaluates performance under resource contention (Network, CPU, Cache, etc.) and with fault injection to simulate real-world conditions.
- **Interactive Visualization**: 📈📊 Leveraging Bokeh as an in-browser renderer, EtherTime can display interactive timeseries of your profiles, which you can explore to your hearts content. 

### Time Synchronization Protocols

EtherTime currently supports four implementations of time synchronization protocols:

1. **PTPd**: An established, if dated, implementation widely deployed due to its simplicity ([Github](https://github.com/ptpd/ptpd)).
2. **LinuxPTP**: A robust implementation tightly integrated with Linux, leveraging kernel and hardware features ([Website](https://www.linuxptp.org/)).
3. **SPTP**: Meta's custom protocol, claiming increased resource efficiency and resilience ([Github](https://github.com/facebook/time/tree/main/ptp)).
4. **Chrony**: A state-of-the-art NTP server/client offering extensive features and capabilities ([Website](https://chrony-project.org/)).

### Embedded Platforms

EtherTime has been tested to work on the following platforms with Ubuntu 22.04 and Debian 11:

- **Raspberry Pi 4 and 5**: Featuring hardware timestamping and integrated real-time clocks.
- **Xilinx ZUBoard 1CG**: Combining ARM Cortex A53 and R5F cores, adapted for Debian with Xilinx Kernels.
- **NVIDIA Jetson TK-1**: 32-bit ARMv7 boards running Ubuntu 22.04 LTS with a customized kernel.

### Evaluation Metrics

EtherTime performs evaluations across several sets of benchmarks:

- **Baseline Performance**: Standard performance without additional load or faults.
- **Resource Contention**: Performance under network, cpu, memory and auxiliary subsystem contention.
- **Fault Tolerance**: Behavior and reliability in the presence of faults originating from hardware or software.
- **Scalability/Resource Consumption**: Analysis of scalability and resource usage as the number of slaves handled by the server increase.

## Getting Started

To start using EtherTime, follow these steps:

**Clone the Repository**:
 
```bash
 git clone https://github.com/[redacted]/ethertime.git
 cd ethertime
 ```

### Installing Dependencies

Refer to [Installing Dependencies](doc/ethertime/dependencies.md) for instructions on setting up the EtherTime project on a local cluster. It covers the installation of Python dependencies, time synchronization packages (linuxptp, chrony, ptpd), and resource contention tools (iPerf, Stress-NG). 
EtherTime requires a database to function, and PostgreSQL is recommended for this purpose. 

### Configuring EtherTime

To allow EtherTime to use your testbed, the network layout and nodes used need to be specified into machines and clusters. The configuration is done in the `config.py` file in the `ptp_perf` directory. Refer to [Configuring EtherTime](doc/ethertime/config.md) for details on how to define machines and clusters in the configuration, as well as the inline comments in `config.py` that help with the layout of the default configuration and specific settings.

### Starting the Scheduler

The `scheduler.py` script in the `ptp_perf` directory is a command-line tool for managing runnable tasks in the EtherTime project. Refer to [Using the Scheduler](doc/ethertime/scheduler.md) for instructions on running the scheduler, adding tasks to the queue, and retrieving the queue status. Every benchmark is a task that can be queued and executed by the scheduler, allowing for unattended operation of the testbed.

### Data Analysis

EtherTime provides a web interface for data visualization and analysis. The interface is built using Django and Bokeh, and it allows users to view and interact with the collected data. The interface supports both interactive summary tables that can be sorted and filtered and interactive time series plots that can be zoomed and panned for detailed inspection. 

## Contributions

Contributions to EtherTime are welcome. Please fork the repository and submit pull requests with your enhancements and bug fixes.

## Contact

For questions or support, please open an issue on the GitHub repository or contact the maintainers at [redacted].
