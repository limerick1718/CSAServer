import logging
import os

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

import sys

sys.path.append("/home/jkliu/Projects/CSAServer")


from core import util
from core import const

logger = logging.getLogger("similarity_cal")


def read_graph_embedding(embedding_file):
    embedding_map = {}
    with open(embedding_file) as f:
        for line in f.readlines():
            line = str(line)
            if ">" in line:
                splitter = line.rfind(">")
                method_name = line[: splitter + 1]
                embedding_str = line[splitter + 1 :]
                embedding = []
                embedding_splits = embedding_str.split()
                for value in embedding_splits:
                    embedding.append(float(value))
                embedding_map[method_name] = np.array(embedding)
    result = pd.DataFrame.from_dict(embedding_map, orient="index")
    return result


def process_node2vec(apk_name: str):
    embedding_file = const.get_embedding_file(apk_name)
    # if os.path.exists(embedding_file):
    #     return
    cg_file = const.get_cg_file(apk_name)
    # if os.path.exists(cg_file) is False:
    print(f"CG file not found for {apk_name}")
    package_name = apk_name.split("-")[0]
    cg_cmd = f"java -jar lib/cg_extractor/target/cgextractor-1.0-SNAPSHOT-jar-with-dependencies.jar -apkPath apks/{apk_name}.apk -androidJar lib/platforms -resultDir results/cg/{apk_name}/CallGraphInfo -packageName {package_name}"
    # cg_cmd = f"java -jar lib/ICCBot.jar -path apks/ -name {apk_name}.apk androidJar lib/platforms -time 30 -maxPathNumber 100 -client MainClient -outputDir results/cg -noLibCode"
    print(cg_cmd)
    os.system(cg_cmd)
    embedding_cmd = f"pecanpy --input {cg_file} --output {embedding_file} --mode FirstOrderUnweighted --delimiter ' -> '"
    print(embedding_cmd)
    os.system(embedding_cmd)


def calculate_similarity(apk_name: str):
    # process_node2vec(apk_name)
    embedding_file = const.get_embedding_file(apk_name)
    similarity7_file = const.get_similarity_file(apk_name, 0.7)
    similarity9_file = const.get_similarity_file(apk_name, 0.9)
    index_file = const.get_index_file(apk_name)
    # if pathlib.Path(similarity7_file).exists() and pathlib.Path(similarity9_file).exists() and pathlib.Path(index_file).exists():
    #     return
    logger.info(f"Calculating similarity for {apk_name}")
    print(f"Read embedding for {apk_name}")
    X = read_graph_embedding(embedding_file)
    # save index to index_file
    with open(index_file, "w") as f:
        for index in X.index:
            f.write(f"{index}\n")
    print(f"Calculating similarity for {apk_name}")
    similarity = cosine_similarity(X, X)
    print(f"Writing similarity for {apk_name}")
    n7 = similarity >= 0.7
    with open(similarity7_file, "wb") as f:
        np.save(f, n7)
    n9 = similarity >= 0.9
    with open(similarity9_file, "wb") as f:
        np.save(f, n9)


if __name__ == "__main__":
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
            cmd = f'cp "{old_apk_path}" {new_apk_path}'
            print(cmd)
            os.system(cmd)
            apk_name = new_name
            calculate_similarity(apk_name)
        except Exception as e:
            logger.error(f"Failed to process {apk_name}")
            failed_apks.append(apk_name)
            logger.error(e)
    if len(failed_apks) > 0:
        print("**************************************************")
        print(f"Failed to process {failed_apks}")
        print("**************************************************")
        logger.error(f"Failed to process {failed_apks}")

# python similarity_cal.py com.zhiliaoapp.musically-2022903010
# python similarity_cal.py org.woheller69.spritpreise-24
# Failed to process ['com.imdb.mobile-109070200', 'com.mxtech.videoplayer.ad-2001002445']