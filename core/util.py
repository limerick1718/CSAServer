# run shell command: sh apk_package.sh {apk_name} and get the output in string
import os
import subprocess

from core import const
import logging

logger = logging.getLogger("util")
permission_mappings = {}


def get_new_name(apk_name: str):
    output = subprocess.check_output(["sh", "apk_package.sh", apk_name]).decode("utf-8")
    return output.strip()

def get_call_graph(apk_name: str):
    cg_path = const.get_cg_file(apk_name)
    if not os.path.exists(cg_path):
        subprocess.Popen(["java", "-jar", "lib/ICCBot.jar", "-path", "apks/", "-name", apk_name + ".apk", "androidJar", "lib/platforms", "-time", "30", "-maxPathNumber", "100", "-client", "CallGraphClient", "-outputDir", "results/cg"])


def parse_permission_method(method: str):
    # android.accounts.AccountManager.getAccounts()android.accounts.Account[]
    method_name = method.split("(")[0].split(".")[-1]
    class_name = method.split("(")[0].replace(f".{method_name}", "")
    return_value = method.split(")")[1]
    params = method.split("(")[1].split(")")[0]
    # <cf.playhi.freezeyou.MainApplication: void <clinit>()>
    return f"<{class_name}: {return_value} {method_name}({params})>"

def read_permission_mappings():
    global permission_mappings
    os.walk("config/mappings")
    for root, dirs, files in os.walk("config/mappings"):
        for file in files:
            if file == "permission_api.txt":
                with open(f"{root}/{file}", "r") as f:
                    lines = f.readlines()
                    for line in lines:
                        line = line.strip()
                        if line.startswith("Permission:"):
                            permission = line.split(":")[1].strip()
                            permission_mappings[permission] = []
                        else:
                            method = line
                            permission_mappings[permission].append(method)
                    continue
            with open(f"{root}/{file}", "r") as f:
                lines = f.readlines()
                for line in lines:
                    try:
                        splits = line.strip().split(" :: ")
                        method = splits[0]
                        permissions = splits[1]
                        method = parse_permission_method(method)
                        permissions = permissions.split(",")
                        for permission in permissions:
                            if permission not in permission_mappings:
                                permission_mappings[permission] = []
                            permission_mappings[permission].append(method)
                    except Exception as e:
                        logger.error(f"Error parsing line: {line}")
                        logger.error(e)

    logger.debug(f"permission_mappings: {permission_mappings}")

def get_permission_api(permission: str):
    if len(permission_mappings) == 0:
        read_permission_mappings()
    return permission_mappings.get(permission, [])

def parse_method_signature(method):
    # method = <de.blau.android.HelpViewer: void onConfigurationChanged(android.content.res.Configuration)>
    try:
        method = method.strip()
        method = method[1:-1]
        method = method.split(':')
        class_name = method[0]
        method = method[1].strip()
        return_value, method = method.split(' ')
        method = method.strip()
        method = method.split('(')
        method_name = method[0].strip()
        params = method[1][:-1].strip().split(',')
        return class_name, return_value, method_name, params
    except Exception as e:
        logger.error(f"Error parsing method: {method}")
        logger.error(e)
        return "", "", "", ""

def is_skipped_package(method_name: str):
    class_name, _, _, _ = parse_method_signature(method_name)
    skipped_package_prefix = ["android",
                              "androidx.",
                              "kotlin.",
                              "com.google.",
                              "soot.",
                              "junit.",
                              "java.",
                              "javax.",
                              "sun.",
                              "org.apache.",
                              "org.eclipse.",
                              "org.junit.",
                              "com.fasterxml.",
                              "com.android"
                              ]
    for temp_package_prefix in skipped_package_prefix:
        if class_name.startswith(temp_package_prefix):
            return True
    return False

def parse_manifest(apk_name: str):
    manifest_path = const.get_manifest_file(apk_name)
    permissions = []
    activities = []
    permission_flag = False
    activity_flag = False
    with open(manifest_path, "r") as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line.startswith("uses-permission"):
                permission_flag = True
                continue
            if line.startswith("activity"):
                activity_flag = True
                continue
            if permission_flag and line.startswith("- name: "):
                permission_flag = False
                permission = line.replace("- name: ", "").strip()
                permissions.append(permission)
                continue
            if activity_flag and line.startswith("- name: "):
                activity_flag = False
                activity = line.replace("- name: ", "").strip()
                activities.append(activity)
                continue
    return permissions, activities