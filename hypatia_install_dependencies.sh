#!/bin/bash

# Main information
echo "Hypatia: installing dependencies"
echo ""
echo "It is highly recommend you use a recent Linux operating system (e.g., Debian 12 / Ubuntu 24.04)."
echo ""

# General System Dependencies
echo "Installing core build tools and Python headers..."
sudo apt-get update || exit 1
sudo apt-get install -y build-essential cmake ninja-build git python3 python3-dev python3-pip patch || exit 1

# satgenpy system deps
echo "Installing mapping dependencies for satgenpy..."
sudo apt-get install -y libproj-dev proj-data proj-bin libgeos-dev || exit 1

# ns3-sat-sim & paper system deps
echo "Installing OpenMPI and testing dependencies for ns3-sat-sim..."
sudo apt-get install -y openmpi-bin openmpi-common openmpi-doc libopenmpi-dev lcov gnuplot || exit 1

# Determine pip flags based on Python version
PIP_FLAGS="--user"
if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 12) else 1)'; then
    echo "Python 3.12+ detected. Applying PEP 668 bypass..."
    PIP_FLAGS="--user --break-system-packages"
else
    echo "Python < 3.12 detected. Using standard pip installation..."
fi

# Python dependencies
echo "Installing Python dependencies via requirements.txt..."
pip3 install $PIP_FLAGS -r requirements.txt || exit 1

# ns3-sat-sim
echo "Applying Git network fixes to prevent submodule disconnects..."
git config --global http.version HTTP/1.1
git config --global http.postBuffer 524288000

echo "Pulling down submodules..."
git submodule update --init --recursive || exit 1

# Confirmation dependencies are installed
echo ""
echo "Hypatia dependencies have been successfully installed!"