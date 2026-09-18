import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():

    xacro_path = os.path.join(
        get_package_share_directory('manip_revis_description'),
        'urdf', 'Manip_revis.xacro'
    )

    moveit_config = (
        MoveItConfigsBuilder("Manip_revis", package_name="manip_revis_moveit_config")
        .robot_description(file_path=xacro_path)
        .robot_description_semantic(file_path="config/manip_revis.srdf")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .joint_limits(file_path="config/joint_limits.yaml")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl"], default_planning_pipeline="ompl")
        .to_moveit_configs()
    )

    # Sobrescreve o pipeline ompl com os parâmetros do nosso ompl_planning.yaml
    moveit_config.planning_pipelines["ompl"] = os.path.join(
        get_package_share_directory('manip_revis_moveit_config'),
        'config', 'ompl_planning.yaml'
    )

    move_group_node = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        output='screen',
        parameters=[moveit_config.to_dict()],
    )

    rviz_config = os.path.join(
        get_package_share_directory('manip_revis_moveit_config'),
        'config', 'moveit.rviz'
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
        ],
    )

    return LaunchDescription([
        move_group_node,
        rviz_node,
    ])
