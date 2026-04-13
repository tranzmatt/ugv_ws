FROM arm64v8/ros:jazzy-ros-base

# Install build deps
RUN apt-get update && apt-get install -y \
    python3-colcon-common-extensions \
    python3-rosdep \
    git \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Cache-bust the clone when the repo changes:
#   docker build --build-arg CACHEBUST=$(date +%s) ...
ARG CACHEBUST=1
RUN git clone https://github.com/tranzmatt/ugv_ws.git /ros2_ws

WORKDIR /ros2_ws

RUN apt-get update && \
    . /opt/ros/jazzy/setup.sh && \
    rosdep update && \
    rosdep install --from-paths src --ignore-src -r -y && \
    # apriltag must be cmake-installed before colcon sees apriltag_ros
    cd src/ugv_else/apriltag_ros/apriltag && \
    cmake -B build -DCMAKE_BUILD_TYPE=Release && \
    cmake --build build --target install && \
    cd /ros2_ws && \
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
