import os
import sys

sys.path.append("/home/jkliu/Projects/CSAServer")

from core import util
import json

short_full_mapping = json.load(open("lib/permission_mapping.json"))
full_short_mapping = {v: k for k, v in short_full_mapping.items()}


def get_exported_activities(apk_path):
    activities = set()
    cmd = f"aapt dump xmltree {apk_path} AndroidManifest.xml"
    lines = os.popen(cmd).read().split("\n")
    is_activity = False
    activity_name = ""
    for line in lines:
        try:
            if "E: activity" in line:
                is_activity = True
            if "A: android:name" in line:
                name = line.split('=\"')[1].split('\" (Raw:')[0]
                if is_activity:
                    activity_name = name
            if "A: android:exported" in line and "0xffffffff" in line and is_activity and activity_name != "":
                activities.add(activity_name)
                activity_name = ""
                is_activity = False
        except:
            print(f"Error while parse line: {line}")
    return activities


def extract_mapping(apk_path, output_path):
    if os.path.exists(output_path):
        return
    apk_name = apk_path.split("/")[-1].replace(".apk", "")
    permissions, _ = util.parse_manifest(apk_name)
    permission_string = ""
    for permission in permissions:
        if permission in full_short_mapping:
            permission = full_short_mapping[permission]
            permission_string += permission + ","
    permission_string = permission_string[:-1]
    cmd = f"java -jar lib/permission/target/permission-1.0-SNAPSHOT-jar-with-dependencies.jar -outputFile {output_path} -androidJar lib/platforms -apkPath {apk_path} -toDebloatPermissions {permission_string}"
    os.system(cmd)


def post_process(apk_path, raw_output, output_path):
    exported_activites = get_exported_activities(apk_path)
    skipped_permissions = set()
    with open(raw_output, "r") as readFile:
        lines = readFile.readlines()
        for line in lines:
            in_exported = False
            short_permission = line.split(":")[0]
            method = line.replace(short_permission + ":", "").strip()
            for activity in exported_activites:
                if activity in method:
                    # if "onCreate" in method or "onStart" in method or "onResume" in method or "onPause" in method or "onStop" in method or "onDestroy" in method or "<init>" in method or "<clinit>" in method:
                    print(f"Skip {method} because it is in an exported activity {activity}")
                    in_exported = True
                    continue
            if in_exported:
                skipped_permissions.add(short_permission)
    print(f"Skipped permissions: {skipped_permissions}")
    with open(f"{output_path.replace('.txt', '_skipped_permissions.txt')}", "w") as write2file:
        for permission in skipped_permissions:
            write2file.write(f"{permission}\n")
    with open(output_path, "w") as write2file:
        with open(raw_output, "r") as readFile:
            lines = readFile.readlines()
            for line in lines:
                in_exported = False
                short_permission = line.split(":")[0]
                if short_permission in skipped_permissions:
                    continue
                method = line.replace(short_permission + ":", "").strip()
                if not in_exported:
                    if short_permission in short_full_mapping:
                        full_permission = short_full_mapping[short_permission]
                        write2file.write(f"{full_permission}:{method}\n")


apks_dir = "apks"
apks = os.listdir(apks_dir)
for apk in apks:
    try:
        if apk.endswith(".apk"):
            apk_path = f"{apks_dir}/{apk}"
            apk_name = apk_path.split("/")[-1].replace(".apk", "")
            print(f"Processing {apk_name}")
            raw_mapping_output_path = f"results/cg/{apk_name}/permission_methods_temp.txt"
            extract_mapping(apk_path, raw_mapping_output_path)
            output_path = f"results/cg/{apk_name}/permission_methods.txt"
            post_process(apk_path, raw_mapping_output_path, output_path)
    except:
        print(f"fail to process {apk}")

# extract_mapping("apks/org.wikipedia.dev-50496.apk")
# post_process("apks/org.wikipedia.dev-50496.apk")
