import os
from core.cg import CG
# "results/cg"

import logging

logger = logging.getLogger("cg_container")

cg_dict = {}
for apk_name in os.listdir("results/cg"):
    cg_dict[apk_name] = CG(apk_name)
    logger.info(f"Load cg for {apk_name}")

def get_cg(apk_name: str):
    return cg_dict[apk_name]