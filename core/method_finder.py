import pandas as pd

from core import const, util
from core.cg import CG

import logging

logger = logging.getLogger("MethodFinder")


class MethodFinder:
    def __init__(self, apk_name: str, neeed_slicing: bool = False):
        self.cg = CG(apk_name)
        self.neeed_slicing = neeed_slicing
        self.apk_name = apk_name
        self.to_remove_methods = []
        self.executed_methods = []

    def set_to_remove_permission(self, permissions: list):
        # save to
        for permission in permissions:
            to_remove_methods = []
            logger.info(f"Debloat permission {permission} for {self.apk_name}")
            permission_methods = set(util.get_permission_api(permission))
            app_methods = set(self.cg.methods)
            intersection = list(permission_methods & app_methods)
            for method in intersection:
                to_remove_methods.append(method)
            logger.info(f"permission_methods: {to_remove_methods}")
            self.to_remove_methods.extend(to_remove_methods)
        self.slicing()

    def set_to_remove_activity(self, activities: list):
        to_remove_methods = []
        for activity in activities:
            logger.info(f"Debloat activity {activity} for {self.apk_name}")
            members = self.cg.get_members(activity)
            logger.info(f"activity_methods: {members}")
            to_remove_methods.extend(members)
        self.to_remove_methods.extend(to_remove_methods)
        if self.neeed_slicing:
            self.slicing()

    def set_executed_methods(self, executed_methods: list):
        self.executed_methods = executed_methods

    def find_proceed_methods(self, to_keep_methods: list, similarities: pd.DataFrame):
        sources_dict = self.cg.sources
        to_process_list = to_keep_methods.copy()
        while len(to_process_list) > 0:
            method = to_process_list.pop()
            if method not in sources_dict:
                continue
            sources = sources_dict[method]
            intersection = list(set(sources) & set(to_keep_methods))
            if len(sources) == 1:
                to_keep_methods.append(sources[0])
                to_process_list.append(sources[0])
                continue
            if len(intersection) == 0:
                if method in similarities:
                    similarity = similarities[method]
                    max_similarity_method = similarity[sources].idxmax()
                    to_keep_methods.append(max_similarity_method)
                    to_process_list.append(max_similarity_method)
        return to_keep_methods

    def generalization(self, threshold: float):
        to_keep_methods = self.executed_methods.copy()
        similarities = pd.read_csv(const.get_similarity_file(self.apk_name), index_col=0)
        for method in self.executed_methods:
            similarity = similarities[method]
            similar_methods = similarity[similarity > threshold].index
            to_keep_methods.extend(similar_methods.to_list())
        to_keep_methods = list(set(to_keep_methods))
        related_methods = self.find_proceed_methods(to_keep_methods, similarities)
        to_remove_methods = list(set(self.cg.methods) - set(related_methods))
        for method in to_remove_methods:
            if util.is_skipped_package(method):
                to_remove_methods.remove(method)
        return to_remove_methods

    def slicing(self):
        dst_srcs_dict = self.cg.sources
        src_dsts_dict = self.cg.targets
        buffer = self.to_remove_methods.copy()
        removed_methods = self.to_remove_methods
        while len(buffer) > 0:
            for method in buffer:
                buffer.remove(method)
                if util.is_skipped_package(method):
                    continue
                if method in dst_srcs_dict:
                    srcs = dst_srcs_dict[method]
                    for src in srcs:
                        if src in src_dsts_dict:
                            dsts = src_dsts_dict[src]
                            dsts.remove(method)
                            if len(dsts) == 0:
                                src_dsts_dict.pop(src)
                                buffer.append(src)
                            src_dsts_dict[src] = dsts
                    dst_srcs_dict.pop(method)
                if method in src_dsts_dict:
                    dsts = src_dsts_dict[method]
                    for dst in dsts:
                        if dst in dst_srcs_dict:
                            srcs = dst_srcs_dict[dst]
                            srcs.remove(method)
                            if len(srcs) == 0:
                                dst_srcs_dict.pop(dst)
                                buffer.append(dst)
                            dst_srcs_dict[dst] = srcs
                    src_dsts_dict.pop(method)
            removed_methods.extend(buffer)
        return removed_methods

    def get_removed_methods(self):
        # for method in self.to_remove_methods:
        #     if util.is_skipped_package(method):
        #         self.to_remove_methods.remove(method)
        return set(self.to_remove_methods)

