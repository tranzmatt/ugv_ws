FROM arm64v8/ros:jazzy-ros-base

# Install deps
RUN apt update && apt install -y \
    python3-colcon-common-extensions \
    python3-rosdep \
    git

RUN git clone https://github.com/tranzmatt/ugv_ws.git /ros2_ws

# Set workspace
WORKDIR /ros2_ws

#COPY ./src ./src
# Build your code
RUN . /opt/ros/jazzy/setup.sh && \
    rosdep update && rosdep install --from-paths src --ignore-src -r -y && \
    ./build_first.sh && \
    ./build_common.sh && \
    ./build_apriltag.sh && \
    colcon build
# Default launch command
ENTRYPOINT ["/bin/bash"]
