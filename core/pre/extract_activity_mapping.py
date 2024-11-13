import os
import sys

sys.path.append("/home/jkliu/Projects/CSAServer")

from core import util
import json

def extract_mapping(apk_path):
    apk_name = apk_path.split("/")[-1].replace(".apk", "")
    output_path = f"results/cg/{apk_name}/activity_methods_temp.txt"
    cmd = f"java -jar lib/activity/target/activity-1.0-SNAPSHOT-jar-with-dependencies.jar -outputFile {output_path} -androidJar lib/platforms -apkPath {apk_path}"
    os.system(cmd)

apks_dir = "apks"
apks = os.listdir(apks_dir)
for apk in apks:
    try:
        if apk.endswith(".apk") and apk != "com.zhiliaoapp.musically-2022903010.apk":
            apk_path = f"{apks_dir}/{apk}"
            apk_name = apk_path.split("/")[-1].replace(".apk", "")
            output_path = f"results/cg/{apk_name}/activity_methods_temp.txt"
            if os.path.exists(output_path):
                print(f"{output_path} exist")
                continue
            print(f"Processing {apk_name}")
            extract_mapping(apk_path)
    except:
        print(f"fail to process {apk}")

# extract_mapping("apks/org.wikipedia.dev-50496.apk")
# post_process("apks/org.wikipedia.dev-50496.apk")