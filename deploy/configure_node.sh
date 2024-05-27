#!/usr/bin/env bash

set -x

sudo apt install -y tmux iperf stress-ng ptpd linuxptp chrony || exit 255

# Alternative: redhat (build ptp chrony from source, linuxptp installed as ptp)
# sudo dnf install -y tmux iperf2 stress-ng || exit 255

pip3 install --user --break-system-packages "rpyc==6.0.0" "pydantic==2.6.2" "pandas==2.2.1" "matplotlib==3.8.3" "scipy==1.12.0" "seaborn==0.13.2" "natsort==8.4.0" "tinytuya==1.13.2" "django==5.0.2" "psycopg==3.1.18" "psycopg_binary==3.1.18" "django-admin-actions==0.1.1" "psutil==5.9.8" "bokeh==3.4.1" || exit 255

echo "Installing ssh keys"
sudo bash -c "umask 077 && mkdir -p ~/.ssh && echo 'ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBDf+fowl76P6HzxBXJTDwDZKeyXFfIcXKH68i/9d3x5SRzDMk2ChLHILGaVtRv7ARd044qnjslpU7lj4AmYsiUI= laptop_key' > ~/.ssh/authorized_keys"
sudo su rpi bash -c "umask 077 && mkdir -p ~/.ssh && echo 'ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBDf+fowl76P6HzxBXJTDwDZKeyXFfIcXKH68i/9d3x5SRzDMk2ChLHILGaVtRv7ARd044qnjslpU7lj4AmYsiUI= laptop_key' > ~/.ssh/authorized_keys"

echo "Don't forget to disable the desktop environment (e.g. using raspi-config)"


echo "Use sudo nmtui to configure the wired interface"
#echo "Add the following to a file in nano /etc/network/interfaces.d/benchmark_interface.conf:
#auto eth0
#iface eth0 inet static
#  address 10.0.0.<IP>
#  netmask 255.255.255.0
#  gateway 10.0.0.1
#"

echo "Copy over the PPSi and SPTP libraries as well."
# Run this as RPI
mkdir -p ~/ptp-perf
#rsync -av 'rpi@192.168.1.106:~/ptp-perf/lib' '/home/rpi/ptp-perf/'
#rsync -av 'rpi@192.168.1.106:~/go' '/home/rpi/'

# sudo rm -rf /home/rpi/go /home/rpi/ptp-perf/lib
rsync -av 'rpi@10.0.0.6:~/ptp-perf/lib' '/home/rpi/ptp-perf/'
rsync -av 'rpi@10.0.0.6:~/go' '/home/rpi/'
