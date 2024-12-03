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

# Check zip
echo -n "Checking if zip is installed: "
if command -v zip &>/dev/null; then
    echo "zip is installed."
else
    echo "zip is not installed."
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

echo "All health checks passed!" 