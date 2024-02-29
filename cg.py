import const
import logging

logger = logging.getLogger("CG")

class CG:
    def __init__(self, apk_name: str):
        self.apk_name = apk_name
        self.methods = set()
        self.sources = {}
        self.targets = {}
        self.members = {}
        cg_file_path = const.get_cg_file(apk_name)
        with open(cg_file_path, "r") as f:
            lines = f.readlines()
            for line in lines:
                src, tgt = line.split(" -> ")
                src = src.strip()
                tgt = tgt.strip()
                self.add_edge(src, tgt)

    def get_class_name(self, method_name: str):
        return method_name[1:].split(": ")[0]

    def add_edge(self, src, tgt):
        self.methods.add(src)
        self.methods.add(tgt)
        if tgt not in self.sources:
            self.sources[tgt] = []
        self.sources[tgt].append(src)

        if src not in self.targets:
            self.targets[src] = []
        self.targets[src].append(tgt)

        src_class = self.get_class_name(src)
        if src_class not in self.members:
            self.members[src_class] = []
        self.members[src_class].append(src)
        tgt_class = self.get_class_name(tgt)
        if tgt_class not in self.members:
            self.members[tgt_class] = []
        self.members[tgt_class].append(tgt)

    def get_sources(self, tgt):
        return self.sources[tgt]

    def get_targets(self, src):
        return self.targets[src]

    def get_members(self, class_name):
        if class_name not in self.members:
            logger.debug(f"Classes in {self.apk_name} are {self.members.keys()}")
            return []
        return self.members[class_name]




