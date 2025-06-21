#!/bin/bash

echo "Running health checks..."

# Check Python version
echo -n "Checking Python version (should be >= 3.6): "
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
if python3 -c 'import sys; assert sys.version_info >= (3,6)' &>/dev/null; then
    echo "Python $PYTHON_VERSION is installed."
else
    echo "Python $PYTHON_VERSION is installed, but version >= 3.6 is required."
    exit 1
fi

# Check if pip is installed
echo -n "Checking pip installation: "
if command -v pip3 &>/dev/null; then
    echo "pip is installed."
else
    echo "pip is not installed."
    exit 1
fi

# Check installed Python packages
echo "Checking Python packages from requirements.txt..."
if [ -s requirements.txt ]; then
    MISSING_PACKAGES=0
    while read -r package; do
        if [[ $package == \#* ]] || [[ -z $package ]]; then
            continue
        fi
        PACKAGE_NAME=$(echo $package | cut -d'=' -f1)
        if ! pip3 show "$PACKAGE_NAME" &>/dev/null; then
            echo "Package $PACKAGE_NAME is not installed."
            MISSING_PACKAGES=1
        else
            echo "Package $PACKAGE_NAME is installed."
        fi
    done < requirements.txt

    if [ $MISSING_PACKAGES -ne 0 ]; then
        echo "Some Python packages are missing."
        exit 1
    fi
else
    echo "No Python packages required."
fi

# Check lsof
echo -n "Checking if lsof is installed: "
if command -v lsof &>/dev/null; then
    echo "lsof is installed."
else
    echo "lsof is not installed."
    exit 1
fi

# Check GPG installation
echo -n "Checking if gpg is installed: "
if command -v gpg &>/dev/null; then
    echo "gpg is installed."
else
    echo "gpg is not installed."
    exit 1
fi

# Check mdatp
echo -n "Checking if mdatp is installed and running: "
if command -v mdatp &>/dev/null; then
    REAL_TIME_PROTECTION=$(mdatp health --field real_time_protection_enabled)
    if [[ $REAL_TIME_PROTECTION == "true" ]]; then
        echo "mdatp is installed and real-time protection is enabled."
    else
        echo "mdatp is installed but real-time protection is not enabled."
        exit 1
    fi
else
    echo "mdatp is not installed."
    exit 1
fi


# # Install safety if not present
# echo -n "Checking if safety is installed: "
# if ! command -v safety &>/dev/null; then
#     echo "safety not found, installing..."
#     pip3 install safety
# else
#     echo "safety is installed."
# fi

# Check Python packages for known vulnerabilities
echo "Checking installed Python packages for vulnerabilities..."
if safety check; then
    echo "No known vulnerabilities found in installed packages."
else
    echo "WARNING: Vulnerabilities found in installed packages!"
fi

# Check requirements.txt for known vulnerabilities
echo "Checking requirements.txt for vulnerabilities..."
if [ -f requirements.txt ]; then
    if safety check -r requirements.txt; then
        echo "No known vulnerabilities found in requirements.txt"
    else
        echo "WARNING: Vulnerabilities found in requirements.txt!"
    fi
else
    echo "requirements.txt not found, skipping check."
fi

# Check system packages for security updates
echo "Checking system packages for security updates..."

# Detect package manager and check for security updates
if command -v apt-get &>/dev/null; then
    sudo apt-get update -qq
    SECURITY_UPDATES=$(apt list --upgradable 2>/dev/null | grep -i security)
elif command -v dnf &>/dev/null; then
    sudo dnf check-update --security -q
    SECURITY_UPDATES=$?
elif command -v yum &>/dev/null; then
    sudo yum check-update --security -q
    SECURITY_UPDATES=$?
else
    echo "Package manager not supported for security update checks (supported: apt, dnf, yum)"
    SECURITY_UPDATES=""
fi

# Handle results based on package manager
if command -v apt-get &>/dev/null; then
    if [ -n "$SECURITY_UPDATES" ]; then
        echo "WARNING: Security updates are available:"
        echo "$SECURITY_UPDATES"
    else
        echo "No security updates available."
    fi
elif command -v dnf &>/dev/null || command -v yum &>/dev/null; then
    if [ $SECURITY_UPDATES -eq 100 ]; then
        echo "WARNING: Security updates are available"
    elif [ $SECURITY_UPDATES -eq 0 ]; then
        echo "No security updates available."
    else
        echo "Error checking for security updates"
    fi
fi

echo "All health checks passed!" 



# # ... existing code ...

# # Check mdatp
# echo -n "Checking if mdatp is installed and running: "
# if command -v mdatp &>/dev/null; then
#     # Check if mdatp service is running and real-time protection is enabled
#     REAL_TIME_PROTECTION=$(mdatp health --field real_time_protection_enabled)
#     ENGINE_STATE=$(mdatp health --field engine_state)
#     if [[ $REAL_TIME_PROTECTION == "true" ]] && [[ $ENGINE_STATE == "active" ]]; then
#         echo "mdatp is installed and running properly."
        
#         # Test scan capability
#         echo -n "Testing mdatp scan capability: "
#         TEST_FILE=$(mktemp)
#         echo "test content" > "$TEST_FILE"
#         if mdatp scan file --path "$TEST_FILE" &>/dev/null; then
#             echo "mdatp scan is working."
#             rm -f "$TEST_FILE"
#         else
#             echo "mdatp scan test failed."
#             rm -f "$TEST_FILE"
#             exit 1
#         fi
#     else
#         echo "mdatp is installed but not running properly. Real-time protection: $REAL_TIME_PROTECTION, Engine state: $ENGINE_STATE"
#         exit 1
#     fi
# else
#     echo "mdatp is not installed."
#     exit 1
# fi

# # Check zip with encryption support
# echo -n "Checking if zip supports encryption: "
# TEST_ZIP=$(mktemp -d)/test.zip
# TEST_FILE=$(mktemp)
# echo "test" > "$TEST_FILE"
# if echo "test_password" | zip -e "$TEST_ZIP" "$TEST_FILE" &>/dev/null; then
#     echo "zip encryption is working."
#     rm -f "$TEST_ZIP" "$TEST_FILE"
# else
#     echo "zip encryption test failed."
#     rm -f "$TEST_ZIP" "$TEST_FILE"
#     exit 1
# fi

# # Check write permissions
# echo "Checking write permissions:"
# for DIR in "$SOURCE_PATH" "$DESTINATION_PATH" "$QUARANTINE_PATH" "$HAZARD_ARCHIVE_PATH"; do
#     if [ -n "$DIR" ]; then
#         echo -n "  Checking $DIR: "
#         if [ -d "$DIR" ]; then
#             TEST_FILE="$DIR/.write_test"
#             if touch "$TEST_FILE" 2>/dev/null; then
#                 echo "writable"
#                 rm -f "$TEST_FILE"
#             else
#                 echo "not writable"
#                 exit 1
#             fi
#         else
#             echo "directory does not exist"
#             exit 1
#         fi
#     fi
# done

# ... existing code ...