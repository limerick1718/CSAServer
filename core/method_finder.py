import logging

import numpy as np

from core import util

logger = logging.getLogger("MethodFinder")


class MethodFinder:
    def __init__(self, package_name, version_code, neeed_slicing: bool = False):
        self.neeed_slicing = neeed_slicing
        self.apk_name = f"{package_name}-{version_code}"
        self.package_name = package_name

    def set_to_remove_permission(self, permissions: list):
        logger.info(f"Debloat permission {permissions} for {self.apk_name}")
        permission_mapping_file = f"results/cg/{self.apk_name}/permission_methods.txt"
        permission_dict = {}
        with open(permission_mapping_file, "r") as file:
            lines = file.readlines()
            for line in lines:
                permission = line.strip().split(":")[0]
                method = line.replace(permission + ":", "").strip()
                if permission not in permission_dict:
                    permission_dict[permission] = set()
                permission_dict[permission].add(method)
        to_remove_methods = set()
        for permission in permissions:
            if permission in permission_dict:
                to_remove_methods.update(permission_dict[permission])
        # to_remove_methods = self.slicing(to_remove_methods)
        # to_remove_methods = self.app_method_slicing(to_remove_methods)
        return to_remove_methods, permissions

    def get_used_permissions(self):
        permission_mapping_file = f"results/cg/{self.apk_name}/permission_methods.txt"
        permission_dict = {}
        with open(permission_mapping_file, "r") as file:
            lines = file.readlines()
            for line in lines:
                permission = line.strip().split(":")[0]
                method = line.replace(permission + ":", "").strip()
                if permission not in permission_dict:
                    permission_dict[permission] = set()
                permission_dict[permission].add(method)
        return permission_dict.keys()

    def set_to_remove_activity(self, activities: list, update_permission: bool = False):
        to_remove_methods = []
        to_remove_permissions = []
        activity_methods_mapping = util.get_activities_with_mapping(self.apk_name)
        for activity in activities:
            logger.info(f"Debloat activity {activity} for {self.apk_name}")
            if activity not in activity_methods_mapping:
                continue
            activity_methods = activity_methods_mapping[activity]
            logger.info(f"activity_methods: {activity_methods}")
            to_remove_methods.extend(activity_methods)
        return to_remove_methods, to_remove_permissions

    def filter_to_remove_methods(self, to_remove_methods: list):
        result = []
        for method in to_remove_methods:
            # if util.is_skipped_package(method):
            #     continue
            if "<init>" in method or "<clinit>" in method:
                continue
            # if android lifecycle method
            if "onCreate" in method or "onStart" in method or "onResume" in method or "onPause" in method or "onStop" in method or "onDestroy" in method:
                continue
            if "dummyMainClass" in method:
                continue
            result.append(method)
        logger.info(f"to_remove_methods size after filter : {len(result)}")
        return result


    def keep_activity_only(self, executed_methods: list):
        _, activities = util.parse_manifest(self.apk_name)
        logger.info(f"declared activities: {activities}")
        executed_activity = set()
        activities = set(activities)
        executed_methods = set(executed_methods)
        for executed_method in executed_methods:
            for activity in activities:
                if activity in executed_method:
                    executed_activity.add(activity)
        logger.info(f"executed activities: {executed_activity}")
        non_executed_activities = activities - executed_activity
        logger.info(f"non-executed activities: {non_executed_activities}")
        to_remove_methods = set()
        activity_methods_mapping = util.get_activities_with_mapping(self.apk_name)
        for activity in non_executed_activities:
            activity_methods = activity_methods_mapping.get(activity, set())
            to_remove_methods.update(activity_methods)
        to_remove_methods = to_remove_methods - executed_methods
        to_remove_methods = list(to_remove_methods)
        result = self.filter_to_remove_methods(to_remove_methods)
        return result


