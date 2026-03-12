#!/bin/bash
# postinstall.sh

# Reload systemd
systemctl --user daemon-reload || true

echo "Installation complete. To enable the service, run:"
echo "  systemctl --user enable --now geforcenow-presence"
