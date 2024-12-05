#!/bin/bash

# Constants
KEY_NAME="hazard_encryption_key@shuttle-linux.py"
KEY_COMMENT="Shuttle Linux Hazard Archive Encryption Key"
EXPIRY="0" # Never expire
KEY_TYPE="RSA"
KEY_LENGTH="4096"

# Generate key configuration file
cat > shuttle_key_config <<EOF
%echo Generating Shuttle Linux GPG key pair
Key-Type: $KEY_TYPE
Key-Length: $KEY_LENGTH
Name-Real: Shuttle Linux
Name-Comment: $KEY_COMMENT
Name-Email: $KEY_NAME
Expire-Date: $EXPIRY
%no-protection
%commit
%echo Done
EOF

# Generate the key pair
gpg --batch --generate-key shuttle_key_config

# Export public key
gpg --armor --export $KEY_NAME > shuttle_public.gpg

# Export private key (keep secure!)
gpg --armor --export-secret-keys $KEY_NAME > shuttle_private.gpg

# Clean up
rm shuttle_key_config

echo "Keys generated successfully:"
echo "Public key: shuttle_public.gpg"
echo "Private key: shuttle_private.gpg"
echo
echo "Key fingerprint:"
gpg --fingerprint $KEY_NAME 