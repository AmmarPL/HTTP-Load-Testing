#!/bin/bash
docker run \
  -v "$(pwd)/Latency_Plots:/app/Latency_Plots" \
  -v "$(pwd)/Pattern_Plots:/app/Pattern_Plots" \
  loadtester "$@"
