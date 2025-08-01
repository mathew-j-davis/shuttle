#!/bin/bash
# sudo -u shuttle_defender_test_runner ./launch_defender_test_and_env.sh
source {{env vars script}}
source {{venv activate}}
run-shuttle-defender-test