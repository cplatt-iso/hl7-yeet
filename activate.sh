#!/bin/bash
# Activate the Python virtual environment for this project
# Usage: source activate.sh

if [ -d "venv" ]; then
    echo "Activating Python virtual environment..."
    source venv/bin/activate
    echo "Virtual environment activated. Python version: $(python --version)"
    echo "Use 'deactivate' to exit the virtual environment."
else
    echo "Error: venv directory not found. Run 'python3 -m venv venv' first."
    exit 1
fi
