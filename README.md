![EtherTime](doc/project/res/logo_nobg.svg)
# EtherTime: Precision Time Synchronization Evaluation Tools
### Overview

EtherTime is an open-source benchmarking tool developed to evaluate the performance of various time synchronization protocols on Ethernet-based distributed systems. This tool is designed to assess the strengths and weaknesses of the supported implementations in different configurations, focusing on dependability and fault tolerance.

### Key Features

- **Cross-Vendor Evaluation**: Supports fair and comparable evaluation of four implementations of time synchronization protocols.
- **Distributed Testbed**: Operates on a testbed consisting of diverse hardware, including Raspberry Pi, Xilinx AVNet, and NVIDIA Jetson boards.
- **Automatic Resource Contention and Fault Injection**: Evaluates performance under resource contention (Network, CPU, Cache, etc.) and with fault injection to simulate real-world conditions.

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

1. **Clone the Repository**:
    ```bash
    git clone https://github.com/[redacted]/ethertime.git
    cd ethertime
    ```
   
2. **Install Dependencies:**
  
EtherTime depends on Python3.11 or greater. Additionally, the vendor packages need to be installed for each vendor that will be evaluated. For resource contention tests, Stress-NG and iPerf are required.

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

Install time synchronization packages:

_Note: Installing Chrony may cause systemd-timesyncd to be uninstalled_

```bash
sudo apt update
sudo apt install linuxptp chrony ptpd
```

Install resource contention tools:

```bash
sudo apt update
sudo apt install iperf stress-ng
```

Finally, Python libraries need to be installed.

```bash
pip3 install -r requirements.txt
```

**Configuring the Database (PostgreSQL)**

EtherTime relies on Django as its database abstraction layer and to serve graphics and data tables. To start profiling, a database that is accessible from all nodes in the testbed is required. We use PostgreSQL but any other supported database should also be compatible.

**Note**: only one database is required for the entire cluster.

To set up PostgreSQL for use with EtherTime, follow these steps:
1. Install PostgreSQL

First, install PostgreSQL on your system.

On Ubuntu:

```bash

sudo apt update
sudo apt install postgresql postgresql-contrib
```

On CentOS/RHEL:

```bash

sudo yum install postgresql-server postgresql-contrib
sudo postgresql-setup initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

2. Configure PostgreSQL

Start the PostgreSQL service and ensure it runs at startup.

On Ubuntu, Debian and CentOS/RHEL::

```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

3. Create a PostgreSQL Database and User

Log in to the PostgreSQL shell as the postgres user:

```bash
sudo -i -u postgres
psql
```

Create a new database and user for EtherTime:

```sql
CREATE DATABASE ethertimedb;
CREATE USER ethertimeuser WITH PASSWORD 'ethertimepassword';
```

Set the correct privileges:

```sql
ALTER ROLE ethertimeuser SET client_encoding TO 'utf8';
ALTER ROLE ethertimeuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE ethertimeuser SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE ethertimedb TO ethertimeuser;
```

5. Configure EtherTime Django Settings

Edit your EtherTime project's settings.py file to configure the database settings.

```python

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ethertimedb',
        'USER': 'ethertimeuser',
        'PASSWORD': 'ethertimepassword',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```
6. Apply Migrations

Apply the initial migrations to set up the database schema.

```bash
python manage.py makemigrations
python manage.py migrate
```

7. Verify the Setup

Run the Django development server to verify that everything is configured correctly.

```bash
python manage.py runserver
```

Visit http://127.0.0.1:8000/ in your web browser. If everything is set up correctly, EtherTime should now be running using the PostgreSQL database.

**Additional Configuration**

For production deployment, you might want to perform additional configurations such as setting up a firewall, configuring SSL, and optimizing the PostgreSQL settings. Refer to the official Django documentation and PostgreSQL documentation for more detailed information.

**Configure the Testbed:**

Edit the `config.py` file in the `ptp_perf` directory to match your testbed setup. The configuration is divided into machines and clusters that will later be used to benchmark on.


## Contributions

Contributions to EtherTime are welcome. Please fork the repository and submit pull requests with your enhancements and bug fixes.

## Contact

For questions or support, please open an issue on the GitHub repository or contact the maintainers at [redacted].
