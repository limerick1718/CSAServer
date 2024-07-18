import os

upload_temp_dir = "upload_temp"
apk_dir = "apks"
cg_dir = "results/cg"
log = "log"

# make directory if not exist
os.makedirs(upload_temp_dir, exist_ok=True)
os.makedirs(apk_dir, exist_ok=True)
os.makedirs(cg_dir, exist_ok=True)


def get_cg_file(apk_name: str):
    os.makedirs(f"{cg_dir}/{apk_name}/CallGraphInfo", exist_ok=True)
    return f"{cg_dir}/{apk_name}/CallGraphInfo/cg.txt"


def get_embedding_file(apk_name: str):
    embeeding_dir = f"results/embedding/node2vec/{apk_name}"
    os.makedirs(embeeding_dir, exist_ok=True)
    return f"results/embedding/node2vec/{apk_name}/embedding.csv"


def get_similarity_file(apk_name: str, threshold: float):
    similarity_dir = f"results/embedding/node2vec/{apk_name}"
    os.makedirs(similarity_dir, exist_ok=True)
    return f"results/embedding/node2vec/{apk_name}/similarity_{threshold}.npy"


def get_index_file(apk_name: str):
    similarity_dir = "results/embedding/node2vec/{apk_name}"
    os.makedirs(similarity_dir, exist_ok=True)
    return f"results/embedding/node2vec/{apk_name}/index.csv"


def get_manifest_file(apk_name: str):
    return f"results/cg/{apk_name}/ManifestInfo/AndroidManifest.txt"
