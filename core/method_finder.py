import logging

import numpy as np

from core import util
from core.cg import CG

logger = logging.getLogger("MethodFinder")


class MethodFinder:
    def __init__(self, package_name, version_code, cg: CG, neeed_slicing: bool = False):
        self.cg: CG = cg
        self.neeed_slicing = neeed_slicing
        self.apk_name = f"{package_name}-{version_code}"
        self.package_name = package_name

    def set_to_remove_permission(self, permissions: list):
        logger.info(f"Debloat permission {permissions} for {self.apk_name}")
        to_remove_methods = []
        for permission in permissions:
            logger.info(f"Debloat permission {permission} for {self.apk_name}")
            permission_methods = set(util.get_permission_api(permission))
            app_methods = set(self.cg.methods)
            intersection = list(permission_methods & app_methods)
            for method in intersection:
                to_remove_methods.append(method)
            logger.info(f"permission_methods: {to_remove_methods}")
        to_remove_methods = self.slicing(to_remove_methods)
        # to_remove_methods = self.app_method_slicing(to_remove_methods)
        return to_remove_methods, permissions

    def get_permission_acitivity_mapping(self):
        result_dict = {}
        permissions, activities = util.parse_manifest(self.apk_name)
        for activity in activities:
            to_remove_permissions = []
            logger.info(f"Debloat activity {activity} for {self.apk_name}")
            members = self.cg.get_members(activity)
            logger.info(f"activity_methods size: {len(members)}")
            to_remove_methods = self.forward_slicing(members)
            logger.info(f"toremove methods size: {len(to_remove_methods)}")
            for permission in permissions:
                permission_methods = set(util.get_permission_api(permission))
                intersection_remove = list(permission_methods & set(to_remove_methods))
                if len(intersection_remove) > 0:
                    to_remove_permissions.append(permission)
            result_dict[activity] = to_remove_permissions
        return result_dict

    def get_used_permissions(self):
        used_permissions = set()
        all_methods = set(self.cg.methods)
        permissions, _ = util.parse_manifest(self.apk_name)
        for permission in permissions:
            permission_methods = set(util.get_permission_api(permission))
            intersection_remove = list(permission_methods & all_methods)
            if len(intersection_remove) > 0:
                used_permissions.add(permission)
        return used_permissions

    def set_to_remove_activity(self, activities: list, update_permission: bool = False):
        to_remove_methods = []
        to_remove_permissions = []
        for activity in activities:
            logger.info(f"Debloat activity {activity} for {self.apk_name}")
            members = self.cg.get_members(activity)
            logger.info(f"activity_methods: {members}")
            to_remove_methods.extend(members)
        if self.neeed_slicing:
            to_remove_methods = self.slicing(to_remove_methods)
        if update_permission:
            permissions, activities = util.parse_manifest(self.apk_name)
            to_keep_methods = list(set(self.cg.methods) - set(to_remove_methods))
            for permission in permissions:
                permission_methods = set(util.get_permission_api(permission))
                intersection_remove = list(permission_methods & set(to_remove_methods))
                intersection_keep = list(permission_methods & set(to_keep_methods))
                if len(intersection_remove) > 0 and len(intersection_keep) == 0:
                    to_remove_permissions.append(permission)
        # currently, debloating activity looks good. We did not filter out activity lifecycle methods.
        # If the result is not good, we can filter out activity lifecycle methods.
        # to_remove_methods = self.filter_to_remove_methods(to_remove_methods)
        return to_remove_methods, to_remove_permissions

    def find_proceed_methods(self, to_keep_methods: list):
        sources_dict = self.cg.sources
        to_process_list = to_keep_methods.copy()
        while len(to_process_list) > 0:
            method = to_process_list.pop()
            try:
                if method not in sources_dict:
                    continue
                sources = sources_dict[method]
                intersection = list(set(sources) & set(to_keep_methods))
                if len(intersection) == 0:
                    to_keep_methods.append(list(sources)[0])
                    to_process_list.append(list(sources)[0])
            except Exception as e:
                logger.error(f"Error processing method: {method}")
                logger.error(e)
                pass
        return to_keep_methods

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

    def keep_only(self, executed_methods: list):
        to_keep_methods = executed_methods.copy()
        to_remove_methods = list(set(self.cg.methods) - set(to_keep_methods))
        result = self.filter_to_remove_methods(to_remove_methods)
        return result

    def generalization(self, executed_methods: list, similarity_matrix, indices: list):
        to_keep_methods_indices = []
        for method in executed_methods:
            if method not in indices:
                continue
            index = indices.index(method)
            to_keep_methods_indices.append(index)
            similarity = similarity_matrix[index]
            similar_methods_indices = np.where(similarity == True)[0]
            to_keep_methods_indices.extend(similar_methods_indices)
        to_keep_methods = [indices[i] for i in to_keep_methods_indices]
        related_methods = self.find_proceed_methods(to_keep_methods)
        logger.info(f"related_methods: {related_methods}")
        to_remove_methods = list(set(self.cg.methods) - set(related_methods))
        result = self.filter_to_remove_methods(to_remove_methods)
        return result

    def forward_slicing(self, to_remove_methods):
        src_dsts_dict = self.cg.targets
        buffer = to_remove_methods.copy()
        while len(buffer) > 0:
            method = buffer.pop()
            if method in src_dsts_dict:
                dsts = src_dsts_dict[method]
                buffer.extend(dsts)
                to_remove_methods.extend(dsts)
        return to_remove_methods

    def backward_slicing(self, to_remove_methods):
        dst_srcs_dict = self.cg.sources
        processed = set()
        buffer = to_remove_methods.copy()
        processed.update(set(buffer))
        while len(buffer) > 0:
            method = buffer.pop()
            if method in dst_srcs_dict:
                srcs = set(dst_srcs_dict[method])
                new_srcs = srcs.difference(processed)
                buffer.extend(new_srcs)
                processed.update(set(new_srcs))
                to_remove_methods.extend(new_srcs)
        logger.info(f"to_remove_methods size : {len(to_remove_methods)}")
        to_remove_methods = self.filter_to_remove_methods(to_remove_methods)
        return to_remove_methods

    def one_step_backward_slicing(self, to_remove_methods):
        dst_srcs_dict = self.cg.sources
        result = []
        for method in to_remove_methods:
            if method in dst_srcs_dict:
                result.extend(dst_srcs_dict[method])
        result.extend(to_remove_methods)
        result = list(set(result))
        return result

    def slicing(self, to_remove_methods):
        dst_srcs_dict = self.cg.sources.copy()
        src_dsts_dict = self.cg.targets.copy()
        buffer = to_remove_methods.copy()
        while len(buffer) > 0:
            method = buffer.pop()
            if method in dst_srcs_dict:
                srcs = set(dst_srcs_dict.pop(method))
                for src in srcs:
                    if src in src_dsts_dict:
                        dsts: set = src_dsts_dict[src]
                        dsts.discard(method)
                        if len(dsts) == 0:
                            src_dsts_dict.pop(src)
                            buffer.append(src)
                        src_dsts_dict[src] = dsts
            if method in src_dsts_dict:
                dsts = src_dsts_dict.pop(method)
                for dst in dsts:
                    buffer.append(dst)
                    if dst in dst_srcs_dict:
                        srcs: set = dst_srcs_dict[dst]
                        srcs.discard(method)
                        if len(srcs) == 0:
                            dst_srcs_dict.pop(dst)
                            buffer.append(dst)
                        dst_srcs_dict[dst] = srcs
        to_remove_methods.extend(buffer)
        return to_remove_methods

    def app_method_slicing(self, to_remove_methods):
        result = set()
        dst_srcs_dict = self.cg.sources
        processed = set()
        buffer = to_remove_methods.copy()
        processed.update(set(buffer))
        while len(buffer) > 0:
            method = buffer.pop()
            if method in dst_srcs_dict:
                srcs = set(dst_srcs_dict[method])
                sliced_app_methods = util.keep_package_only(list(srcs), [self.package_name])
                result.update(sliced_app_methods)
                if len(sliced_app_methods) > 0:
                    print(f"method: {method}, sliced_app_methods: {sliced_app_methods}")
                srcs.difference_update(sliced_app_methods)
                srcs.difference_update(processed)
                lib_only_srcs = [src for src in srcs if util.is_skipped_package(src)]
                if len(lib_only_srcs) > 0:
                    srcs = lib_only_srcs
                buffer.extend(srcs)
                processed.update(set(srcs))
        logger.info(f"to_remove_methods size : {len(result)}")
        result = util.keep_package_only(list(result), [self.package_name])
        result = self.filter_to_remove_methods(list(result))
        return list(result)
