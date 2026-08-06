import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = get_package_share_directory('ugv_vision')
    param_file = os.path.join(pkg_dir, 'config', 'hailo_detect.yaml')

    oak_launch = IncludeLaunchDescription(PythonLaunchDescriptionSource(
        [os.path.join(pkg_dir, 'launch'), '/oak_d_lite.launch.py'])
    )

    hailo_detect_node = Node(
        package='ugv_vision',
        executable='hailo_detect',
        name='hailo_detect',
        parameters=[param_file, {'image_topic': '/oak/rgb/image_raw'}],
        output='screen',
    )

    return LaunchDescription([
        oak_launch,
        hailo_detect_node,
    ])
