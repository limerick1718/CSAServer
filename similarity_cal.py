import logging
import os
import pathlib

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from core import const

logger = logging.getLogger("similarity_cal")

def read_graph_embedding(embedding_file):
    embedding_map = {}
    with open(embedding_file) as f:
        for line in f.readlines():
            line = str(line)
            if '>' in line:
                splitter = line.rfind('>')
                method_name = line[:splitter + 1]
                embedding_str = line[splitter + 1:]
                embedding = []
                embedding_splits = embedding_str.split()
                for value in embedding_splits:
                    embedding.append(float(value))
                embedding_map[method_name] = np.array(embedding)
    result = pd.DataFrame.from_dict(embedding_map, orient='index')
    return result

def process_node2vec(apk_name: str):
    embedding_file = const.get_embedding_file(apk_name)
    if os.path.exists(embedding_file):
        return
    cg_file = const.get_cg_file(apk_name)
    if not pathlib.Path(cg_file).exists():
        logger.info(f"CG file not found for {apk_name}")
        os.system(f"java -jar lib/ICCBot.jar -path apks/ -name {apk_name}.apk androidJar lib/platforms -time 30 -maxPathNumber 100 -client CallGraphClient -outputDir results/cg")
    print(f"pecanpy --input {cg_file} --output {embedding_file} --mode FirstOrderUnweighted --delimiter ' -> '")
    os.system(f"pecanpy --input {cg_file} --output {embedding_file} --mode FirstOrderUnweighted --delimiter ' -> '")

def calculate_similarity(apk_name: str):
    process_node2vec(apk_name)
    embedding_file = const.get_embedding_file(apk_name)
    similarity7_file = const.get_similarity_file(apk_name, 0.7)
    similarity9_file = const.get_similarity_file(apk_name, 0.9)
    index_file = const.get_index_file(apk_name)
    if pathlib.Path(similarity7_file).exists() and pathlib.Path(similarity9_file).exists() and pathlib.Path(index_file).exists():
        return
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

if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    # parser.add_argument("apk_name")
    # args = parser.parse_args()
    # apk_name = args.apk_name
    # calculate_similarity(apk_name)
    # util.load_similarity_file(apk_name, 0.7)
    for apk_name in os.listdir("apks"):
        apk_name = apk_name[:-4]
        calculate_similarity(apk_name)

# python similarity_cal.py com.zhiliaoapp.musically-2022903010
# python similarity_cal.py org.woheller69.spritpreise-24