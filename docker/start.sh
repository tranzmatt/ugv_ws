#!/bin/bash
# Run the ugv_ws jazzy container with hardware access and display forwarding.
# Usage:
#   ./docker/start.sh                      # interactive shell
#   ./docker/start.sh "ros2 launch ..."    # run a specific command
#
# Pass --build to rebuild the image first:
#   ./docker/start.sh --build

IMAGE="ugv_ws_jazzy"
BUILD=0

if [ "$1" = "--build" ]; then
    BUILD=1
    shift
fi

if [ "$BUILD" = "1" ]; then
    docker build -t "$IMAGE" -f "$(dirname "$0")/Dockerfile" .
fi

CMD="${1:-bash}"

docker run -it --rm \
  --name ugv_jazzy \
  --network host \
  --ipc host \
  --privileged \
  -v /dev:/dev \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -e DISPLAY="$DISPLAY" \
  -e UGV_MODEL="${UGV_MODEL:-ugv_rover}" \
  "$IMAGE" \
  "$CMD"
