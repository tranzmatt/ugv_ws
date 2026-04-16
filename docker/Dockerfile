FROM arm64v8/ros:jazzy

SHELL ["/bin/bash", "-c"]
WORKDIR /home/ws/ugv_ws

# Install build deps and add OSRF Gazebo Harmonic apt repo
RUN apt-get update && apt-get install -y \
    python3-colcon-common-extensions \
    python3-rosdep \
    git \
    cmake \
    curl \
    gnupg2 \
    ca-certificates \
    lsb-release && \
    curl -sSL https://packages.osrfoundation.org/gazebo.gpg \
      -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] \
      https://packages.osrfoundation.org/gazebo/ubuntu-stable $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
      > /etc/apt/sources.list.d/gazebo-stable.list && \
    rm -rf /var/lib/apt/lists/*

# Default: copy local source (always reflects current working tree).
# To build straight from GitHub instead, pass --build-arg USE_GIT=1:
#   docker build --build-arg USE_GIT=1 -f docker/Dockerfile .
# Run from the repo root so the build context contains ./src.
ARG USE_GIT=0

RUN if [ "$USE_GIT" = "1" ]; then \
        git clone -b ros2-jazzy-develop \
            https://github.com/tranzmatt/ugv_ws.git /tmp/ugv_ws_git && \
        cp -r /tmp/ugv_ws_git/. /home/ws/ugv_ws/ && \
        rm -rf /tmp/ugv_ws_git; \
    fi

# Only copy local context when not using git (conditional via shell test after copy)
COPY . /tmp/ugv_ws_ctx/
RUN if [ "$USE_GIT" = "0" ]; then \
        cp -r /tmp/ugv_ws_ctx/. /home/ws/ugv_ws/; \
    fi && \
    rm -rf /tmp/ugv_ws_ctx

RUN apt-get update && \
    . /opt/ros/jazzy/setup.sh && \
    rosdep update && \
    rosdep install --from-paths src --ignore-src -r -y && \
    # apriltag must be cmake-installed before colcon sees apriltag_ros
    cd src/ugv_else/apriltag_ros/apriltag && \
    cmake -B build -DCMAKE_BUILD_TYPE=Release && \
    cmake --build build --target install && \
    cd /home/ws/ugv_ws && \
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
    . install/setup.bash && \
    # Wave 2: ugv application packages
    colcon build --packages-select \
        ugv_bringup ugv_chat_ai ugv_description ugv_gazebo \
        ugv_nav ugv_slam ugv_tools ugv_vision ugv_web_app \
        --symlink-install && \
    rm -rf /var/lib/apt/lists/*

# Set up interactive shell environment
RUN echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc && \
    echo 'eval "$(register-python-argcomplete ros2)"' >> ~/.bashrc && \
    echo 'eval "$(register-python-argcomplete colcon)"' >> ~/.bashrc && \
    echo "source /home/ws/ugv_ws/install/setup.bash" >> ~/.bashrc

ENTRYPOINT ["/bin/bash", "-c"]
CMD ["bash"]
