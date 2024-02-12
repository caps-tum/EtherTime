#!/usr/bin/env bash

set -x

sudo apt install -y tmux iperf stress-ng ptpd linuxptp || exit 255
pip3 install --user --break-system-packages rpyc pydantic pandas matplotlib || exit 255

echo "Don't forget to disable the desktop environment (e.g. using raspi-config)"

echo "Add the following to a file in /etc/network/interfaces.d/benchmark_interface.conf:
auto eth0
iface eth0 inet static
  address 10.0.0.<IP>
  netmask 255.255.255.0
  gateway 10.0.0.1
"

echo "Copy over the PPSi library as well."
