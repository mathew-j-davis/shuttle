#!/bin/bash
# Test script to verify wizard saves to config/install_inputs.yaml

cd /home/mathew/shuttle

# Run wizard and select option 3 (save only) with default filename
./scripts/1_install.sh --wizard <<EOF
1
n
n



n
n
n
n
y
n





y
n








3

EOF

# Check if file was created
if [[ -f "config/install_inputs.yaml" ]]; then
    echo "✅ Instructions file created at default location: config/install_inputs.yaml"
    echo "=== Contents ==="
    cat config/install_inputs.yaml
else
    echo "❌ Instructions file not created at expected location"
fi