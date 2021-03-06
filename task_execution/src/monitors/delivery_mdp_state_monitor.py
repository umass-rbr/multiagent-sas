#!/usr/bin/env python
import json
import os

import roslib
roslib.load_manifest('mid_level_robot_planner')

import rospy
from mid_level_robot_planner.srv import GetLocationSrv
from task_execution.msg import DeliveryMdpState

CURRENT_FILE_PATH = os.path.dirname(os.path.realpath(__file__))
DISTANCE_THRESHOLD = 2.0


def get_nearest_location():
    rospy.wait_for_service('/mid_level_planner/map_management/get_loc')

    try:
        get_location_proxy = rospy.ServiceProxy('/mid_level_planner/map_management/get_loc', GetLocationSrv)
        location_response = get_location_proxy()
        return location_response.curr_loc, location_response.dist_to_loc
    except rospy.ServiceException as exception:
        rospy.loginfo("Could not get location: %s", exception)

    return False


# TODO Implement this function 
def has_package():
    return False


def main():
    rospy.init_node("delivery_mdp_state_monitor", anonymous=True)

    rospy.loginfo("Info[delivery_mdp_state_monitor.main]: Instantiating the delivery_mdp_state_monitor node...")

    publisher = rospy.Publisher("monitor/delivery_mdp_state", DeliveryMdpState, queue_size=10)
    rate = rospy.Rate(rospy.get_param("/delivery_mdp_state_monitor/rate"))

    # TODO Replace this at some point
    world_map = json.load(open(CURRENT_FILE_PATH + '/../tmp/LGRC3_plan_map.json'))

    current_location = None

    while not rospy.is_shutdown():
        message = DeliveryMdpState()

        location, distance = get_nearest_location()
        if current_location is None or (distance < DISTANCE_THRESHOLD and location in world_map['paths'][current_location]):
            current_location = location

        message.location = current_location
        message.has_package = has_package()

        publisher.publish(message)

        rate.sleep()


if __name__ == '__main__':
    main()
