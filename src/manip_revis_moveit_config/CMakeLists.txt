cmake_minimum_required(VERSION 3.8)
project(manip_revis_moveit_config)

find_package(ament_cmake REQUIRED)

install(DIRECTORY config launch scripts
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
