import argparse
import pathlib

import networkx as nx
import numpy as np
import pandas as pd
from node2vec import Node2Vec

from sklearn.metrics.pairwise import cosine_similarity

from core import const

import logging

import util

logger = logging.getLogger("similarity_cal")

apk_name = "org.isoron.uhabits-149"


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
    cg_file = const.get_cg_file(apk_name)
    if not pathlib.Path(cg_file).exists():
        logger.info(f"CG file not found for {apk_name}")
    else:
        write2fileName = const.get_embedding_file(apk_name)
        write2File = pathlib.Path(write2fileName)
        if not write2File.exists():
            edge_list = []
            logger.info(f"Processing {apk_name}")
            with open(cg_file) as f:
                edges = f.readlines()
                for edge in edges:
                    edge = edge.strip()
                    src, tgt = edge.split(" -> ")
                    if util.is_skipped_package(src) or util.is_skipped_package(tgt):
                        continue
                    edge_list.append([src, tgt])
            df = pd.DataFrame(edge_list, columns=['src', 'tgt'])
            G = nx.from_pandas_edgelist(df, source='src', target='tgt', create_using=nx.Graph())
            node2vec = Node2Vec(G, workers=8)
            model = node2vec.fit()
            model.wv.save_word2vec_format(write2fileName)


def calculate_similarity(apk_name: str):
    embedding_file = const.get_embedding_file(apk_name)
    similarity_file = const.get_similarity_file(apk_name)
    if pathlib.Path(similarity_file).exists():
        return
    logger.info(f"Calculating similarity for {apk_name}")
    X = read_graph_embedding(embedding_file)
    similarity = cosine_similarity(X, X)
    pd.DataFrame(similarity, index=X.index, columns=X.index).to_csv(similarity_file)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("apk_name")
    args = parser.parse_args()
    apk_name = args.apk_name
    process_node2vec(apk_name)
    calculate_similarity(apk_name)