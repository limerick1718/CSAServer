import os


from core import util
from core import const

def get_cg(apk_name: str):
    cg_path = const.get_cg_file(apk_name)
    package_name = apk_name.split("-")[0]
    # if not os.path.exists(cg_path):
    cg_cmd = f"java -jar lib/cg_extractor/target/cgextractor-1.0-SNAPSHOT-jar-with-dependencies.jar -apkPath apks/{apk_name}.apk -androidJar lib/platforms -resultDir results/cg/{apk_name}/CallGraphInfo/cg_raw.txt -packageName {package_name}"
    print(cg_cmd)
    os.system(cg_cmd)

if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    # parser.add_argument("apk_name")
    # args = parser.parse_args()
    # apk_name = args.apk_name
    # calculate_similarity(apk_name)
    # util.load_similarity_file(apk_name, 0.7)
    temp_uploaded_file_path = f"{const.upload_temp_dir}"
    failed_apks = []
    for apk_name in os.listdir(temp_uploaded_file_path):
        print(apk_name)
        try:
            if not apk_name.endswith(".apk"):
                continue
            old_apk_path = os.path.join(temp_uploaded_file_path, apk_name)
            print(f"processing {old_apk_path}")
            new_name = util.get_new_name(old_apk_path)
            new_apk_path = f"{const.apk_dir}/{new_name}.apk"
            # copy the file to the apk directory
            cmd = f"cp \"{old_apk_path}\" {new_apk_path}"
            print(cmd)
            os.system(cmd)
            apk_name = new_name
            get_cg(apk_name)
        except Exception as e:
            failed_apks.append(apk_name)
    if len(failed_apks) > 0:
        print("**************************************************")
        print(f"Failed to process {failed_apks}")
        print("**************************************************")
        print(f"Failed to process {failed_apks}")

# python similarity_cal.py com.zhiliaoapp.musically-2022903010
# python similarity_cal.py org.woheller69.spritpreise-24