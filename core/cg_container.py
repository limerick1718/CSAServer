import os
from core.cg import CG
# "results/cg"

import logging

logger = logging.getLogger("cg_container")

cg_dict = {}

def init():
    for apk_name in os.listdir("results/cg"):
        apk_name = apk_name.replace(".apk", "")
        cg_dict[apk_name] = CG(apk_name)
        logger.info(f"Load cg for {apk_name}")


def get_cg(apk_name: str):
    if apk_name not in cg_dict:
        cg_dict[apk_name] = CG(apk_name)
        logger.info(f"Load cg for {apk_name}")
    return cg_dict[apk_name]

init()