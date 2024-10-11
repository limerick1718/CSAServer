# run shell command: sh apk_package.sh {apk_name} and get the output in string
import os
import subprocess

from urllib.parse import unquote

import numpy as np

from core import const
import logging

logger = logging.getLogger("util")
permission_mappings = {}


def get_new_name(apk_name: str):
    output = subprocess.check_output(["bash", "apk_package.sh", apk_name]).decode("utf-8")
    return output.strip()


def get_call_graph(apk_name: str):
    cg_path = const.get_cg_file(apk_name)
    if not os.path.exists(cg_path):
        print(f"java -jar lib/ICCBot.jar -path apks/ -name {apk_name}.apk androidJar lib/platforms -time 30 -maxPathNumber 100 -client MainClient -outputDir results/cg -noLibCode")
        subprocess.Popen(["java", "-jar", "lib/ICCBot.jar", "-path", "apks/", "-name", apk_name + ".apk", "androidJar", "lib/platforms", "-time", "30", "-maxPathNumber", "100", "-client", "MainClient",
                          "-outputDir", "results/cg", "-noLibCode"])
# java -jar lib/ICCBot.jar -path apks/ -name org.wikipedia.dev-50496.apk androidJar lib/platforms -time 30 -maxPathNumber 100 -client MainClient -outputDir results/cg -noLibCode

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
    skipped_package_prefix = ["<android",
                              "<androidx",
                              "<kotlin",
                              "<com.google",
                              "<soot",
                              "<junit",
                              "<java",
                              "<javax",
                              "<sun",
                              "<org.apache",
                              "<org.eclipse",
                              "<org.junit",
                              "<com.fasterxml",
                              "<com.android"
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


def get_declared_activities(apk_name: str):
    activities = set()
    apk_path = f"{const.apk_dir}/{apk_name}.apk"
    cmd = f"aapt dump xmltree {apk_path} AndroidManifest.xml"
    lines = os.popen(cmd).read().split("\n")
    is_activity = False
    for line in lines:
        if "E: activity" in line:
            is_activity = True
        if is_activity and "A: android:name" in line:
            # print(line)
            activity = line.split('=\"')[1].split('\" (Raw:')[0]
            # print(activity)
            activities.add(activity)
            is_activity = False
    return activities

def load_similarity_file(apk_name: str, threshold: float):
    embedding_file = const.get_similarity_file(apk_name, threshold)
    index_file = const.get_index_file(apk_name)
    indices = []
    with open(index_file, "r") as f:
        lines = f.readlines()
        for line in lines:
            indices.append(line.strip())
    with open(embedding_file, 'rb') as f:
        similarity_matrix = np.load(f)
    return similarity_matrix, indices


def parse_method_signature_from_request(method: str):
    # <int com.google.android.material.color.MaterialColors.getColor(android.content.Context,int,int)> is in the format of <return_value class_name.method_name(parameters)>
    # logger.info(f"parse_method_signature_from_request Method: {method}")
    raw_method = method
    # try:
    method = method.strip()
    # method = method[1:-2]
    return_value = method.split(' ')[0]
    method = method.split(' ')[1]
    params = method.split('(')[1]
    class_name_and_method_name = method.split('(')[0]
    method_name = class_name_and_method_name.split('.')[-1]
    class_name = class_name_and_method_name.replace(f".{method_name}", "")
    # except:
    #     logger.error(f"Error parsing method: {raw_method}")
    #     return ""
    method_signature = f"<{class_name}: {return_value} {method_name}({params})>"
    # print(f"Method Signature: {method_signature}")
    return method_signature


def extract_methods_from_requests(executed_methods_str: str):
    executed_methods_str = unquote(executed_methods_str.strip())
    executed_methods_str = executed_methods_str[1:-1]
    executed_methods = executed_methods_str.split(">,<")
    method_signatures = []
    for method in executed_methods:
        method = method.strip()
        method_signature = parse_method_signature_from_request(method)
        method_signatures.append(method_signature)
    print(method_signatures)
    return method_signatures


def keep_package_only(methods: list, packages: list):
    if "com.zhiliaoapp.musically" in packages:
        packages.append("com.ss.")
        packages.append("com.bytedance.")
    packages = ["<" + package for package in packages]
    result = set()
    logger.info(f"Number of methods before filter package only : {len(methods)}")
    for method in methods:
        is_package_method = False
        for package in packages:
            if method.startswith(package):
                is_package_method = True
                break
        if is_package_method:
            result.add(method)
    logger.info(f"Number of methods AFTER filter package only : {len(result)}")
    return list(result)
