#!/bin/bash

sh setup.sh

# Run tests
python -m unittest discover -s tests
