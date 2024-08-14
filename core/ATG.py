import xml.etree.ElementTree as ET

class ATG(object):
    def __init__(self):
        self.transitions = set()

    def __add_transition__(self, transition: str):
        self.transitions.add(transition)

    def __add_transitions__(self, file_path: str):
        tree = ET.parse(file_path)
        root = tree.getroot()
        sources = root.findall("source")
        for source in sources:
            targets = source.findall("destination")
            if len(targets) == 0:
                continue
            src = source.get("name")
            for target in targets:
                dst = target.get("name")
                transition = f"{src} -> {dst}"
                self.__add_transition__(transition)

    def add_app_transitions(self, app: str, version: str):
        self.__add_transitions__(f"results/cg/{app}-{version}/CTGResult/CTG.xml")
        return self.transitions

    def __str__(self):
        return "\n".join([str(transition) for transition in self.transitions])