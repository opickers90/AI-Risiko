#!/usr/bin/env bash

cd $(dirname $0)
source ./webhook_env_vars.sh
source ./.venv/bin/activate
python webhook_listener.py
