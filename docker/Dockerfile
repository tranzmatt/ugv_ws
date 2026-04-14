FROM arm64v8/ros:jazzy-ros-base

# Install build deps
RUN apt-get update && apt-get install -y \
    python3-colcon-common-extensions \
    python3-rosdep \
    git \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Default: copy local source (always reflects current working tree).
# To build straight from GitHub instead, pass --build-arg USE_GIT=1:
#   docker build --build-arg USE_GIT=1 -f docker/Dockerfile .
# Run from the repo root so the build context contains ./src.
ARG USE_GIT=0
WORKDIR /ros2_ws

RUN if [ "$USE_GIT" = "1" ]; then \
        git clone https://github.com/tranzmatt/ugv_ws.git /ros2_ws_git && \
        cp -r /ros2_ws_git/. /ros2_ws/ && \
        rm -rf /ros2_ws_git; \
    fi

COPY . /ros2_ws/

RUN apt-get update && \
    . /opt/ros/jazzy/setup.sh && \
    rosdep update && \
    rosdep install --from-paths src --ignore-src -r -y && \
    # apriltag must be cmake-installed before colcon sees apriltag_ros
    cd src/ugv_else/apriltag_ros/apriltag && \
    cmake -B build -DCMAKE_BUILD_TYPE=Release && \
    cmake --build build --target install && \
    cd /ros2_ws && \
    ./build_first.sh && \
    ./build_common.sh && \
    ./build_apriltag.sh && \
    # Wave 1: third-party / driver packages
    colcon build --packages-select \
        apriltag apriltag_msgs apriltag_ros \
        cartographer \
        costmap_converter_msgs costmap_converter \
        emcl2 \
        explore_lite \
        openslam_gmapping slam_gmapping \
        ldlidar \
        rf2o_laser_odometry \
        robot_pose_publisher \
        teb_msgs teb_local_planner \
        vizanti vizanti_cpp vizanti_demos vizanti_msgs vizanti_server \
        ugv_base_node ugv_interface && \
    # Wave 2: ugv application packages
    colcon build --packages-select \
        ugv_bringup ugv_chat_ai ugv_description ugv_gazebo \
        ugv_nav ugv_slam ugv_tools ugv_vision ugv_web_app \
        --symlink-install && \
    rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["/bin/bash"]
