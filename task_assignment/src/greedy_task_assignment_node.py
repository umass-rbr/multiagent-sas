#!/usr/bin/env python
import json
import os

import rospy
import utils
from robot import Robot, RobotType
from task_assignment.msg import TaskAssignmentAction, WorldState
from task_handler import DeliveryTaskHandler, EscortTaskHandler

CURRENT_FILE_PATH = os.path.dirname(os.path.realpath(__file__))

PUBLISHER = rospy.Publisher('task_assignment/task_assignment_action', TaskAssignmentAction, queue_size=1)

TASK_MAP = {
    'delivery': {
        'task_handler': DeliveryTaskHandler()
    },
    'escort': {
        'task_handler': EscortTaskHandler()
    }
}

# TODO Implement a topic or service that has this information
PUMPKIN = Robot('Pumpkin', RobotType.TURTLEBOT)
JAKE = Robot('Jackal', RobotType.JACKAL)
SHLOMO = Robot('Human', RobotType.HUMAN)
ROBOTS = [PUMPKIN, JAKE, SHLOMO]


def get_world_map():
    with open(CURRENT_FILE_PATH + '/tmp/LGRC3_plan_map.json') as world_map_file:
        return json.load(world_map_file)


def generate_assignments(tasks, robots):
    options = utils.get_cartesian_product(tasks, robots)
    assignments = utils.get_power_set(options)

    trimmed_assignments = [assignment for assignment in assignments if len(assignment) <= len(tasks)]

    feasible_assignments = []
    for assignment in trimmed_assignments:
        is_feasible = True

        is_task_used = [False for _ in tasks]
        is_robot_used = [False for _ in robots]

        for task, robot in assignment:
            task_index = tasks.index(task)
            robot_index = robots.index(robot)

            if is_task_used[task_index] or is_robot_used[robot_index]:
                is_feasible = False
                break

            is_task_used[task_index] = True
            is_robot_used[robot_index] = True

        if is_feasible:
            feasible_assignments.append(assignment)

    return feasible_assignments


def calculate_expected_cost(assignment, distance_map):
    cost = 0

    for task, robot in assignment:
        cost += robot.get_cost(distance_map, [robot.get_loc(), task.pickup_location, task.dropoff_location])

    return cost


def find_best_assignment(tasks, assignments, distance_map):
    best_assignment = None
    best_expected_cost = float('inf')

    for assignment in assignments:
        expected_cost = calculate_expected_cost(assignment, distance_map) + 1000 * (len(tasks) - len(assignment))

        if expected_cost < best_expected_cost:
            best_assignment = assignment
            best_expected_cost = expected_cost

    return best_assignment, best_expected_cost


def get_tasks(task_info):
    tasks = []

    for key in task_info.keys():
        if task_info[key]['status'] == 'available':
            task_request = task_info[key]['task_request']
            task_handler = TASK_MAP[task_request['type']]['task_handler']
            task = task_handler.get_task(key, task_request['start_time'], task_request['end_time'], 'request', task_request['data'])
            tasks.append(task)

    return tasks


def get_available_robots(robot_info):
    return [robot for robot in ROBOTS if robot_info[robot.name]['status'] == 'available']


def assign(info):
    tasks = get_tasks(info['tasks'])
    available_robots = get_available_robots(info['robots'])

    world_map = get_world_map()
    distance_map = utils.get_distance_map(world_map)

    if available_robots:
        for robot in available_robots:
            robot.set_loc(info['robots'][robot.name]['location'])

        rospy.loginfo('Info[greedy_task_assignment_node.assign]: Generating tasks assignments...')
        assignments = generate_assignments(tasks, available_robots)

        rospy.loginfo('Info[greedy_task_assignment_node.assign]: Determining best assignments...')
        best_assignment, best_cost = find_best_assignment(tasks, assignments, distance_map)

        rospy.loginfo('Info[greedy_task_assignment_node.assign]: Publishing assignments...')
        # for task, robot in best_assignment:
        #     message = TaskAssignmentAction()
        #     message.header.stamp = rospy.Time.now()
        #     message.header.frame_id = "/greedy_task_assignment_node"
        #     message.robot_id = robot.get_name()
        #     message.task_request = task.get_task_request()

        #     rospy.loginfo('Info[greedy_task_assignment_node.assign]: Publishing the assignment: %s', message)
        #     PUBLISHER.publish(message)

    return best_assignment, best_cost


def main():
    with open('tmp/task_and_robot_status_info.json') as f:
        manager_endpoint = ''

        info = json.load(f)
        assignment, _ = assign(info)

        data = {}
        for task, robot in assignment:
            data[robot.get_name()] = task.id

        print(data)

        #r = request.post(url = manager_endpoint, data = data)

if __name__ == '__main__':
    main()
