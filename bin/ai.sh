#!/bin/bash

FOLDER=$(dirname -- "$0")/..

PYTHONPATH=$FOLDER python3 $FOLDER/ai/init.py "$@"