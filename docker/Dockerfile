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
    chmod +x build_apriltag.sh build_first.sh build_common.sh && \
    ./build_apriltag.sh && \
    ./build_first.sh && \
    rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["/bin/bash", "-c"]
CMD ["bash"]
