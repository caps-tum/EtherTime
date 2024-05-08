#!/bin/bash

# Start a new tmux session and detach from it immediately
tmux new-session -d -s ptp-perf

# Rename the first window
tmux rename-window -t ptp-perf 'Scheduler'

# Split the first window vertically with the top pane 66% of the height
tmux split-window -v -l 20%

# Run commands in each pane of the first window
tmux send-keys -t ptp-perf:Scheduler.0 'python3 scheduler.py run' C-m
tmux send-keys -t ptp-perf:Scheduler.1 'watch python3 scheduler.py info' C-m

# Create a new window
tmux new-window -t ptp-perf -n 'Server'

# Split the second window vertically with the top pane 66% of the height
tmux split-window -v -l 20%

# Run commands in each pane of the second window
tmux send-keys -t ptp-perf:Server.0 'python3 manage.py runserver 0.0.0.0:8000' C-m
tmux send-keys -t ptp-perf:Server.1 'deploy/schedule_backups.sh' C-m

# Attach to the session
tmux attach-session -t ptp-perf
