#!/bin/bash

# Exit immediately on error
set -e

python3.11 -m pip install --upgrade pip
pip install -r requirements.txt

mv .env.example .env

# Run tests
python -m unittest discover -s tests
