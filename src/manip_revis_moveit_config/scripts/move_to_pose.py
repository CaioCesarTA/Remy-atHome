#!/usr/bin/env python3
"""
Move a ponta da garra (flange_ferramenta) para uma posição XYZ usando MoveIt2 (moveit_py).

Uso:
  # com Gazebo/robô real já rodando (gazebo.launch.py) e o move_group ativo (moveit.launch.py):
  python3 move_to_pose.py --x 0.15 --y 0.05 --z 0.30

Requer: sudo apt install ros-humble-moveit-py  (se ainda não tiver)
"""
import os
import argparse
import rclpy
from rclpy.logging import get_logger
from ament_index_python.packages import get_package_share_directory

from moveit.planning import MoveItPy
from moveit_configs_utils import MoveItConfigsBuilder
from geometry_msgs.msg import PoseStamped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--x', type=float, required=True, help='posição X (m)')
    parser.add_argument('--y', type=float, required=True, help='posição Y (m)')
    parser.add_argument('--z', type=float, required=True, help='posição Z (m)')
    args, _ = parser.parse_known_args()

    rclpy.init()
    logger = get_logger('move_to_pose')

    # MoveItPy sobe seu próprio nó e precisa da config completa (não reaproveita
    # a do move_group), incluindo o planning_python_api.yaml via .moveit_cpp().
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
        .planning_pipelines(pipelines=["ompl"])
        .moveit_cpp(file_path="config/planning_python_api.yaml")
        .to_moveit_configs()
    )

    manip = MoveItPy(node_name='move_to_pose_client', config_dict=moveit_config.to_dict())
    arm = manip.get_planning_component('arm')

    # Pose alvo para a ponta (flange_ferramenta)
    pose_goal = PoseStamped()
    pose_goal.header.frame_id = 'base_link'
    pose_goal.pose.position.x = args.x
    pose_goal.pose.position.y = args.y
    pose_goal.pose.position.z = args.z
    # Orientação é ignorada pelo solver (position_only_ik: true no
    # kinematics.yaml), já que o braço só tem 3 DOF. Valor aqui é só
    # placeholder para a mensagem ficar válida.
    pose_goal.pose.orientation.w = 1.0

    arm.set_start_state_to_current_state()
    arm.set_goal_state(pose_stamped_msg=pose_goal, pose_link='flange_ferramenta')

    logger.info(f'Planejando trajetória até X={args.x} Y={args.y} Z={args.z} ...')
    plan_result = arm.plan()

    if plan_result:
        logger.info('Plano encontrado, executando...')
        manip.execute(plan_result.trajectory, controllers=[])
    else:
        logger.error('Não foi possível encontrar um plano para essa posição (fora do alcance?).')

    rclpy.shutdown()


if __name__ == '__main__':
    main()
