#!/bin/bash

# Usage information
usage() {
    echo "Usage: $0 [options]"
    echo "Generate GPG key pair for Shuttle encryption"
    echo ""
    echo "Options:"
    echo "  --key-name NAME       Key name/email (default: Shuttle Linux Hazard Archive Encryption Key)"
    echo "  --key-comment COMMENT Key comment (default: Shuttle Linux Hazard Archive Encryption Key)"
    echo "  --output-dir DIR      Output directory (default: current directory)"
    echo "  --public-filename FILE Public key filename (default: shuttle_public.gpg)"
    echo "  --private-filename FILE Private key filename (default: shuttle_private.gpg)"
    echo "  --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Generate production keys"
    echo "  $0 --key-name test_key --output-dir /path/to/test"
    exit 1
}

# Default values (production defaults)
KEY_NAME="Shuttle Linux Hazard Archive Encryption Key"
KEY_COMMENT="Shuttle Linux Hazard Archive Encryption Key"
EXPIRY="0" # Never expire
KEY_TYPE="RSA"
KEY_LENGTH="4096"
OUTPUT_DIR="."
PUBLIC_FILENAME="shuttle_public.gpg"
PRIVATE_FILENAME="shuttle_private.gpg"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --key-name)
            KEY_NAME="$2"
            shift 2
            ;;
        --key-comment)
            KEY_COMMENT="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --public-filename)
            PUBLIC_FILENAME="$2"
            shift 2
            ;;
        --private-filename)
            PRIVATE_FILENAME="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Full paths for output files
PUBLIC_PATH="$OUTPUT_DIR/$PUBLIC_FILENAME"
PRIVATE_PATH="$OUTPUT_DIR/$PRIVATE_FILENAME"

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
gpg --armor --export $KEY_NAME > "$PUBLIC_PATH"

# Export private key (keep secure!)
gpg --armor --export-secret-keys $KEY_NAME > "$PRIVATE_PATH"

# Clean up
rm shuttle_key_config

echo "Keys generated successfully:"
echo "Public key: $PUBLIC_PATH"
echo "Private key: $PRIVATE_PATH"
echo
echo "Key fingerprint:"
gpg --fingerprint $KEY_NAME 