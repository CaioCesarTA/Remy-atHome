#!/usr/bin/env python3
"""
Move a ponta da garra (flange_ferramenta) em linha reta por uma lista de
waypoints XYZ, usando o serviço /compute_cartesian_path do move_group.

Bom para: aproximação final de pegar um objeto, entrega para uma pessoa
(handover), ou qualquer trecho onde o caminho da ponta precisa ser
previsível (reto), não só o destino.

Uso:
  # com gazebo.launch.py e moveit.launch.py já rodando
  python3 cartesian_move.py --waypoints "0.15,0.05,0.35" "0.15,0.05,0.20"

Cada --waypoints é um ponto "x,y,z" (em metros, relativo ao base_link).
Pode passar vários, na ordem em que devem ser visitados.
"""
import argparse
import rclpy
from rclpy.node import Node
from rclpy.logging import get_logger
from rclpy.action import ActionClient

from moveit_msgs.srv import GetCartesianPath
from moveit_msgs.action import ExecuteTrajectory
from moveit_msgs.msg import RobotState
from geometry_msgs.msg import Pose


class CartesianMover(Node):
    def __init__(self):
        super().__init__('cartesian_move_client')
        self.cartesian_client = self.create_client(
            GetCartesianPath, '/compute_cartesian_path')
        self.execute_client = ActionClient(
            self, ExecuteTrajectory, '/execute_trajectory')

    def move_through(self, waypoints_xyz, max_step=0.01, avoid_collisions=True):
        logger = get_logger('cartesian_move')

        if not self.cartesian_client.wait_for_service(timeout_sec=5.0):
            logger.error('Serviço /compute_cartesian_path indisponível. '
                          'O move_group (moveit.launch.py) está rodando?')
            return False

        request = GetCartesianPath.Request()
        request.header.frame_id = 'base_link'
        request.group_name = 'arm'
        request.link_name = 'flange_ferramenta'
        request.max_step = max_step
        request.jump_threshold = 0.0  # desabilitado (recomendado no ROS2)
        request.avoid_collisions = avoid_collisions
        request.start_state = RobotState()
        request.start_state.is_diff = True  # usa o estado atual do robô como base

        for x, y, z in waypoints_xyz:
            pose = Pose()
            pose.position.x = x
            pose.position.y = y
            pose.position.z = z
            pose.orientation.w = 1.0  # ignorado (position_only_ik: true)
            request.waypoints.append(pose)

        logger.info(f'Calculando caminho cartesiano por {len(waypoints_xyz)} waypoint(s)...')
        future = self.cartesian_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        response = future.result()

        if response is None:
            logger.error('Falha ao chamar /compute_cartesian_path.')
            return False

        logger.info(f'Fração do caminho completada: {response.fraction:.2f}')
        if response.fraction < 0.99:
            logger.warn('Caminho incompleto — algum trecho ficou fora de alcance '
                         'ou bateria em colisão. Executando só o trecho válido.')
        if response.fraction <= 0.0:
            logger.error('Nenhum trecho do caminho é válido. Abortando.')
            return False

        return self._execute(response.solution)

    def _execute(self, robot_trajectory):
        logger = get_logger('cartesian_move')
        if not self.execute_client.wait_for_server(timeout_sec=5.0):
            logger.error('Action /execute_trajectory indisponível.')
            return False

        goal = ExecuteTrajectory.Goal()
        goal.trajectory = robot_trajectory

        logger.info('Executando trajetória...')
        send_future = self.execute_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future)
        goal_handle = send_future.result()

        if not goal_handle.accepted:
            logger.error('Trajetória rejeitada pelo move_group.')
            return False

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        logger.info('Execução concluída.')
        return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--waypoints', nargs='+', required=True,
                         help='pontos "x,y,z" em metros, ex: 0.15,0.05,0.30')
    parser.add_argument('--max-step', type=float, default=0.01,
                         help='resolução da interpolação em metros (padrão 0.01)')
    args = parser.parse_args()

    waypoints = []
    for wp in args.waypoints:
        x, y, z = (float(v) for v in wp.split(','))
        waypoints.append((x, y, z))

    rclpy.init()
    mover = CartesianMover()
    mover.move_through(waypoints, max_step=args.max_step)
    mover.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
