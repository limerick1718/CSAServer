import os
import sys

sys.path.append("/home/jkliu/Projects/CSAServer")

from core import util
import json

short_full_mapping = json.load(open("lib/permission_mapping.json"))
full_short_mapping = {v: k for k, v in short_full_mapping.items()}

def extract_mapping(apk_path):
    apk_name = apk_path.split("/")[-1].replace(".apk", "")
    output_path = f"results/cg/{apk_name}/permission_methods_temp.txt"
    permissions, _ = util.parse_manifest(apk_name)
    permission_string = ""
    for permission in permissions:
        if permission in full_short_mapping:
            permission = full_short_mapping[permission]
            permission_string += permission + ","
    permission_string = permission_string[:-1]
    cmd = f"java -jar lib/permission/target/permission-1.0-SNAPSHOT-jar-with-dependencies.jar -outputFile {output_path} -androidJar lib/platforms -apkPath {apk_path} -toDebloatPermissions {permission_string}"
    os.system(cmd)

def post_process(apk_path):
    apk_name = apk_path.split("/")[-1].replace(".apk", "")
    input_path = f"results/cg/{apk_name}/permission_methods_temp.txt"
    output_path = f"results/cg/{apk_name}/permission_methods.txt"
    with open(output_path, "w") as write2file:
        with open(input_path, "r") as readFile:
            lines = readFile.readlines()
            for line in lines:
                short_permission = line.split(":")[0]
                method = line.replace(short_permission + ":", "").strip()
                if short_permission in short_full_mapping:
                    full_permission = short_full_mapping[short_permission]
                    write2file.write(f"{full_permission}:{method}\n")

apks_dir = "apks"
apks = os.listdir(apks_dir)
for apk in apks:
    try:
        if apk.endswith(".apk") and apk != "com.zhiliaoapp.musically-2022903010.apk":
            apk_path = f"{apks_dir}/{apk}"
            apk_name = apk_path.split("/")[-1].replace(".apk", "")
            output_path = f"results/cg/{apk_name}/permission_methods.txt"
            if os.path.exists(output_path):
                print(f"{output_path} exist")
                continue
            print(f"Processing {apk_name}")
            extract_mapping(apk_path)
            post_process(apk_path)
    except:
        print(f"fail to process {apk}")

# extract_mapping("apks/org.wikipedia.dev-50496.apk")
# post_process("apks/org.wikipedia.dev-50496.apk")