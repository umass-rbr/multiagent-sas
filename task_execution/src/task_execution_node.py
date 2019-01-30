#!/usr/bin/env python
import rospy

from mdps.delivery_mdp import DeliveryMDP
from mdps.escort_mdp import EscortMDP
from task_assignment.msg import TaskAssignmentAction
from task_execution.msg import DeliveryMdpState, EscortMdpState, TaskExecutionAction

action_publisher = rospy.Publisher("task_execution/task_execution_action", TaskExecutionAction, queue_size=1)

delivery_mdp_state = None
escort_mdp_state = None


def delivery_mdp_state_callback(state):
    delivery_mdp_state = state


def escort_mdp_state_callback(state):
    escort_mdp_state = state


# TODO Implement a simple map server
def get_map(task_data):
    rospy.wait_for_service('get_map')
    try:
        get_map = rospy.ServiceProxy('get_map', GetMap)
        res = get_map(task_data.map_name)
        return res
    except rospy.ServiceException, e:
        rospy.logerr("Error[task_execution_node.get_map]: Failed to request map")


def get_problem(task_type, task_data, map):
    if task_type == "delivery":
        return DeliveryMDP(map, task_data.start_location, task_data.end_location)

    if task_type == "escort":
        return EscortMDP(map, task_data.start_location, task_data.end_location)

    return False


# TODO Retrieve the solution from a file if available
def get_solution(task_type, problem):
    if task_type == "delivery":
        return problem.solve()

    if task_type == "escort":
        return problem.solve()

    return False


def get_current_state(task_type):
    if task_type == "delivery":
        return delivery_mdp_state

    if task_type == "escort":
        return escort_mdp_state

    return False


# TODO Get a location name from the policy
# TODO Should the task_assignment object be passed to all functions instead?
# TODO Break out of the code when a failure occurs 
def execute(task_assignment):
    rospy.loginfo("Info[task_execution_node.execute]: Received a task assignment")

    robot_id = rospy.get_param('/task_execution_node/robot_id')
    if task_assignment.robot_id == robot_id:
        map = get_map(task_assignment.task_data)

        problem = get_problem(task_assignment.task_type, task_assignment.task_data, map)
        if not problem:
            rospy.logerr("Error[task_execution_node.execute]: Received an invalid task assignment")
        
        solution = problem.solve()
        if not solution:
            rospy.logerr("Error[task_execution_node.execute]: Received an invalid task assignment")

        state_map = solution["state_map"]
        action_map = solution["action_map"]
        policy = solution["policy"]
        
        current_state = get_current_state(task_assignment.task_type)
        if not current_state: 
            rospy.logerr("Error[task_execution_node.execute]: Received an invalid task assignment")

        while not rospy.is_shutdown():
            new_state = get_current_state(task_assignment.task_type)
            
            if new_state != current_state:
                current_state = new_state
                current_action = action_map[policy[state_map[current_state]]]

                msg = TaskExecutionAction()
                msg.x = map[current_action]["position"]["x"]
                msg.y = map[current_action]["position"]["y"]
                msg.theta = map[current_action]["position"]["theta"]

                rospy.loginfo(msg)
                action_publisher.publish(msg)

            duration = rospy.get_param('/task_execution_node/duration')
            rospy.sleep(duration)


# TODO Separate monitoring code into another file
# TODO Rename everything across all files
# TODO Ensure that task_assigner code is working properly
def main():
    rospy.init_node("task_execution_node", anonymous=True)
    rospy.loginfo("Info[task_execution_node.main]: Instantiated the task_execution node")

    rospy.Subscriber("task_assignment/task_assignment_action", TaskAssignmentAction, execute, queue_size=1)
    rospy.Subscriber("monitor/delivery_mdp_state", DeliveryMdpState, delivery_mdp_state_callback, queue_size=1)
    rospy.Subscriber("monitor/escort_mdp_state", EscortMdpState, escort_mdp_state_callback, queue_size=1)

    rospy.spin()


if __name__ == '__main__':
    main()
