import os
import sys

sys.path.append("/home/jkliu/Projects/CSAServer")

def extract_class_method_mapping(cg_path: str):
    class_method_mapping = {}
    with open(cg_path, "r") as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            src, tgt = line.split(" -> ")
            src, tgt = src.strip(), tgt.strip()
            src_cls = src[1:].split(":")[0]
            if src_cls not in class_method_mapping:
                class_method_mapping[src_cls] = set()
            class_method_mapping[src_cls].add(src)
            tgt_cls = tgt[1:].split(":")[0]
            if tgt_cls not in class_method_mapping:
                class_method_mapping[tgt_cls] = set()
            class_method_mapping[tgt_cls].add(tgt)
    return class_method_mapping

def write_result(class_method_mapping: dict, result_path: str):
    with open(result_path, "w") as f:
        for cls in class_method_mapping:
            for method in class_method_mapping[cls]:
                f.write(f"{cls}:{method}\n")

if __name__ == "__main__":
    cg_path = "/home/jkliu/Projects/CSAServer/results/cg/com.zhiliaoapp.musically-2022903010/CallGraphInfo/cg.txt"
    result_path = "/home/jkliu/Projects/CSAServer/results/cg/com.zhiliaoapp.musically-2022903010/activity_methods_temp.txt"
    class_method_mapping = extract_class_method_mapping(cg_path)
    write_result(class_method_mapping, result_path)