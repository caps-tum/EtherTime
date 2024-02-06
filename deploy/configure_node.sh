#!/usr/bin/env bash

set -x

sudo apt install -y tmux iperf stress-ng ptpd linuxptp || exit 255
pip3 install --user --break-system-packages rpyc pydantic || exit 255
