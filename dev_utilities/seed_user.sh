#!/bin/bash

if [ $# -eq 0 ]
then
    echo "Usage: ./seed_user.sh <username> [--password <password>]"
    exit 1
fi

if ! command -v python3 &> /dev/null
then
    echo "Python 3 is not installed. Please install it and try again."
    exit 1
fi

python3 seed_user.py "$@"
