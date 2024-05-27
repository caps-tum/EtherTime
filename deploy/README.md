# Deployment Utilities

This directory contains utilities for assisting in the deployment of EtherTime on a local cluster. The utilities are designed to automate the process of setting up the EtherTime project on a local cluster, including the installation of Python dependencies, time synchronization packages (linuxptp, chrony, ptpd), and resource contention tools (iPerf, Stress-NG).

### Setup Scripts

We offer scripts for Raspberry Pi and Xilinx 1Board CG, which are tested and verified to work with Ubuntu 22.04 and Debian 11. Refer to `configure_node.sh` and `configure_petalinux.sh` for more information on the installation process.

### Backups

The `schedule_backups.sh` script is a utility tool that automatically creates daily backups of the project's database. It generates a unique label for each backup using the current date, constructs a filename using this label, and then dumps the data from the application into a compressed JSON file. The script then pauses for 24 hours before repeating the process. This ensures that a new, compressed backup of the project's database is created and saved every day. The output of the script is stored in the `local/` directory.

### Running the Server

A fully working server (including Django server, Scheduler, and Backups) is provided in [start_server_tmux.sh](start_server_tmux.sh). This script will start the Django server, Scheduler, and Backups in separate tmux windows. The Django server will be running on port 8000, and the Scheduler output will be visible in the first window along with the remaining tasks. The Backups script will be running in the background.
