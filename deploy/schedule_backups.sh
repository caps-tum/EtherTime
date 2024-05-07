#!/usr/bin/env bash

while true
do
  label="$(date +'%Y-%m-%d')"
  filename="local/db_backup_${label}.json.gz"
  echo "Creating backup at $(date) to $filename"
  python3 manage.py dumpdata app | gzip > "$filename"
  du -ch local/db_backup_*
  echo "Backup completed at $(date) to $filename"
  sleep 86400
done
