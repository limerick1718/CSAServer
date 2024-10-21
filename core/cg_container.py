import os
from core.cg import CG
# "results/cg"

import logging

logger = logging.getLogger("cg_container")

cg_dict = {}

def init():
    for apk_name in os.listdir("results/cg"):
        try:
            apk_name = apk_name.replace(".apk", "")
            cg_dict[apk_name] = CG(apk_name)
            logger.info(f"Load cg for {apk_name}")
        except Exception as e:
            logger.error(f"Fail to load cg for {apk_name}: {e}")
            pass


def get_cg(apk_name: str):
    if apk_name not in cg_dict:
        cg_dict[apk_name] = CG(apk_name)
        logger.info(f"Load cg for {apk_name}")
    return cg_dict[apk_name]

init()