#!/usr/bin/env bash

set -x

sudo apt install -y tmux iperf stress-ng ptpd linuxptp || exit 255
pip3 install --user --break-system-packages rpyc pydantic pandas matplotlib || exit 255

echo "Don't forget to disable the desktop environment (e.g. using raspi-config)"

echo "Copy over the PPSi library as well."
