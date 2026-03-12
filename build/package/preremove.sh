#!/bin/bash
# preremove.sh

# Stop and disable the service
systemctl --user stop geforcenow-presence || true
systemctl --user disable geforcenow-presence || true
