#!/usr/bin/env python3
#
# Copyright 2019 ROBOTIS CO., LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Authors: Joep Tool

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # Get the directory of the launch file
    launch_file_dir = os.path.join(get_package_share_directory('ugv_gazebo'), 'launch/bringup')
    # Get the directory of the ros_gz_sim package (Gazebo Harmonic / Jazzy)
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    # Get the use_sim_time parameter from the launch file
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    # Launch Gazebo Harmonic (gz sim) with an empty world - replaces gzserver + gzclient
    gz_sim_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': 'empty.sdf'}.items()
    )

    # Include the robot_state_publisher launch file
    robot_state_publisher_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(launch_file_dir, 'robot_state_publisher.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    # Include the spawn_ugv launch file
    spawn_ugv_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(launch_file_dir, 'spawn_ugv.launch.py')
        )
    )

    # Bridge Gazebo Harmonic topics to ROS2 (replaces gazebo_ros auto-bridging)
    bridge_config = os.path.join(
        get_package_share_directory('ugv_gazebo'), 'config', 'ros_gz_bridge.yaml'
    )
    ros_gz_bridge_cmd = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'config_file': bridge_config}],
        output='screen',
    )

    # Create a launch description
    ld = LaunchDescription()

    # Add the commands to the launch description
    ld.add_action(gz_sim_cmd)
    ld.add_action(ros_gz_bridge_cmd)
    ld.add_action(robot_state_publisher_cmd)
    ld.add_action(spawn_ugv_cmd)

    return ld
