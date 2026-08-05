#!/bin/bash
# =============================================================================
# sensor_test.sh — self-contained validation test for the USB webcam, OAK-D
# Lite, and LD19 lidar.
#
# Launches each sensor node itself, waits for data, samples the publish
# rate, and tears every node it started back down on exit — nothing is left
# running afterward, and nothing needs to be pre-launched.
#
# This script never touches ugv_bringup / base_node / motors, so it's safe
# to run with the robot sitting on a bench or table.
#
# USAGE
#   ./scripts/sensor_test.sh
#
# PREREQUISITES
#   Runs natively (no Docker). Devices must be present and accessible:
#     /dev/video0   USB webcam        — needs 'video' group
#     /dev/bus/usb  OAK-D Lite        — needs a udev rule (see below)
#     /dev/ttyAMA1  LD19 lidar (UART) — needs 'dialout' group
#   OAK-D udev rule (one-time, host-level):
#     echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' \
#       | sudo tee /etc/udev/rules.d/80-movidius.rules
#     sudo udevadm control --reload-rules && sudo udevadm trigger
#
# EXPECTED RESULTS
#   LD19 lidar     /scan                   ~10 Hz
#   USB webcam     /image_raw              ~25-30 Hz (solo: 30, floor: 15)
#   OAK-D RGB      /oak/rgb/image_raw      ~25-30 Hz (floor: 15)
#   OAK-D depth    /oak/stereo/image_raw   ~15-25 Hz (floor: 10)
#   Running all three sensors together adds real CPU contention on a 4-core
#   Pi — measured dips to ~19 Hz (webcam/RGB) and ~15 Hz (depth) are normal
#   under that load, not a fault. The pass/fail floors above are set below
#   that observed noise floor; they exist to catch a sensor that's actually
#   dead or barely trickling data, not to enforce the solo/quiet numbers.
#
#   If OAK-D fails with X_LINK_ERROR / "No data on logger queue", the device
#   didn't finish releasing its USB connection from a previous run. Wait
#   ~20s and run the script again; unplug/replug the OAK-D if it persists.
# =============================================================================

source /opt/ros/jazzy/setup.bash 2>/dev/null
source /home/ws/ugv_ws.jazzy/install/setup.bash 2>/dev/null

export LDLIDAR_MODEL="${LDLIDAR_MODEL:-ld19}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
PIDS=()
LOGDIR=$(mktemp -d)

cleanup() {
    echo ""
    echo "Tearing down sensor nodes..."
    for pid in "${PIDS[@]:-}"; do
        kill -TERM "-$pid" 2>/dev/null
    done
    # OAK-D's depthai driver needs a few seconds to close its USB/XLink
    # connection cleanly; killing it too fast can wedge the device until it
    # idles out, causing X_LINK_ERROR on the next launch.
    sleep 6
    for pid in "${PIDS[@]:-}"; do
        kill -KILL "-$pid" 2>/dev/null
    done
    rm -rf "$LOGDIR"
}
trap cleanup EXIT INT TERM

# Launches "ros2 $*" in its own session so cleanup() can kill the whole
# process group (ros2 launch spawns child nodes/containers of its own).
launch() {
    local logname="$1"; shift
    setsid ros2 "$@" > "$LOGDIR/$logname.log" 2>&1 &
    PIDS+=("$!")
}

check_topic() {
    local topic="$1" min_rate="$2" label="$3" wait_s="${4:-8}"

    if ! timeout "$wait_s" ros2 topic echo --once "$topic" > /dev/null 2>&1; then
        echo -e "  ${RED}FAIL${NC}  $label ($topic) — no messages received"
        FAIL=$((FAIL + 1))
        return
    fi

    rate=$(timeout 6 ros2 topic hz "$topic" 2>/dev/null \
           | grep "average rate" | tail -1 | awk '{print $3}' | tr -d ':')

    if [ -z "$rate" ]; then
        echo -e "  ${YELLOW}WARN${NC}  $label ($topic) — alive but could not measure rate"
        PASS=$((PASS + 1))
        return
    fi

    rate_int=${rate%.*}
    if [ "$rate_int" -ge "$min_rate" ] 2>/dev/null; then
        echo -e "  ${GREEN}PASS${NC}  $label ($topic) @ ${rate} Hz"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}FAIL${NC}  $label ($topic) @ ${rate} Hz (expected >= ${min_rate} Hz)"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "=== UGV Sensor Test ==="
echo "(camera + lidar only — motors are not touched)"
echo ""

# Start all three up front — OAK-D is the slowest to boot (Myriad VPU init),
# so it's launched first and gets the runtime of the other two checks as a
# head start instead of waiting on its own timeout in series.
echo "Starting sensor nodes..."
launch oak launch ugv_vision oak_d_lite.launch.py
launch lidar launch ldlidar ldlidar.launch.py
launch usb_cam launch ugv_vision camera.launch.py

# Three concurrent `ros2 launch` startups spike CPU hard on a 4-core Pi.
# `ros2 topic echo`/`hz` below are themselves fresh DDS participants that
# need to spin up and discover the publishers — give the initial spawn
# storm time to settle first, or the checker itself can starve and time
# out even though the sensor node is already publishing fine.
sleep 5
echo ""

echo "--- LD19 Lidar ---"
check_topic /scan 8 "LD19 laser scan" 15

echo ""
echo "--- USB Webcam ---"
check_topic /image_raw 15 "USB webcam" 15

echo ""
echo "--- OAK-D Lite ---"
check_topic /oak/rgb/image_raw 15 "OAK-D RGB" 25
check_topic /oak/stereo/image_raw 10 "OAK-D depth" 10

echo ""
echo "========================"
if [ "$FAIL" -eq 0 ]; then
    echo -e "  ${GREEN}All ${PASS} checks passed${NC}"
else
    echo -e "  ${GREEN}${PASS} passed${NC}  ${RED}${FAIL} failed${NC}"
fi
echo ""
