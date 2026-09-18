import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction, AppendEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import xacro
from os.path import join

def generate_launch_description():

    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    # O pacote principal é manip_revis_description
    pkg_ros_gz_rbot = get_package_share_directory('manip_revis_description')

    # Caminhos com a subpasta incluída
    robot_description_file = os.path.join(pkg_ros_gz_rbot, 'urdf', 'Manip_revis.xacro')
    ros_gz_bridge_config = os.path.join(pkg_ros_gz_rbot, 'config', 'ros_gz_bridge_gazebo.yaml')
    
    robot_description_config = xacro.process_file(robot_description_file)
    robot_description = {'robot_description': robot_description_config.toxml()}

    set_env_vars_resources_ign = AppendEnvironmentVariable(
        'IGN_GAZEBO_RESOURCE_PATH',
        os.path.join(pkg_ros_gz_rbot, '..')
    )
    
    set_env_vars_resources_gz = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        os.path.join(pkg_ros_gz_rbot, '..')
    )
    # -----------------------------------

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[robot_description],
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(join(pkg_ros_gz_sim, "launch", "gz_sim.launch.py")),
        launch_arguments={"gz_args": "-r -v 4 empty.sdf"}.items()
    )

    spawn_robot = TimerAction(
        period=5.0,  
        actions=[Node(
            package='ros_gz_sim',
            executable='create',
            arguments=[
                "-topic", "/robot_description",
                "-name", "Manip_revis",
                "-allow_renaming", "false",
                "-x", "0.0",
                "-y", "0.0",
                "-z", "0.0",
                "-Y", "0.0"
            ],
            output='screen'
        )]
    )

    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'config_file': ros_gz_bridge_config}],
        output='screen'
    )

    spawn_broadcaster = TimerAction(
        period=8.0,
        actions=[Node(package='controller_manager', executable='spawner', arguments=['joint_state_broadcaster'])]
    )

    spawn_controller = TimerAction(
        period=10.0,
        actions=[Node(package='controller_manager', executable='spawner', arguments=['arm_controller'])]
    )

    return LaunchDescription([
        set_env_vars_resources_ign,
        set_env_vars_resources_gz,
        gazebo,
        spawn_robot,
        ros_gz_bridge,
        robot_state_publisher,
    ])