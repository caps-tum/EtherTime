#!/usr/bin/env bash

set -x

sudo apt install -y tmux iperf stress-ng ptpd linuxptp || exit 255
pip3 install --user --break-system-packages rpyc pydantic pandas matplotlib 'psycopg[binary]==3.1.18' "django==5.0.2" || exit 255

echo "Installing ssh keys"
sudo bash -c "umask 077 && mkdir -p ~/.ssh && echo 'ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBDf+fowl76P6HzxBXJTDwDZKeyXFfIcXKH68i/9d3x5SRzDMk2ChLHILGaVtRv7ARd044qnjslpU7lj4AmYsiUI= vincent_bode@VTO-Laptop-XPS15' > ~/.ssh/authorized_keys"
sudo su rpi bash -c "umask 077 && mkdir -p ~/.ssh && echo 'ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBDf+fowl76P6HzxBXJTDwDZKeyXFfIcXKH68i/9d3x5SRzDMk2ChLHILGaVtRv7ARd044qnjslpU7lj4AmYsiUI= vincent_bode@VTO-Laptop-XPS15' > ~/.ssh/authorized_keys"

echo "Don't forget to disable the desktop environment (e.g. using raspi-config)"

echo "Add the following to a file in nano /etc/network/interfaces.d/benchmark_interface.conf:
auto eth0
iface eth0 inet static
  address 10.0.0.<IP>
  netmask 255.255.255.0
  gateway 10.0.0.1
"

echo "Copy over the PPSi and SPTP libraries as well."
# Run this as RPI
mkdir -p ~/ptp-perf
rsync -av 'rpi@192.168.1.106:~/ptp-perf/lib' '/home/rpi/ptp-perf/lib'
rsync -av 'rpi@192.168.1.106:~/go' '/home/rpi/go'
