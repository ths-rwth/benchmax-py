from tools.Tool import Tool
from random import shuffle


class Jobs:
    def __init__(self, tools: list[Tool], files: list[str]):
        self.tools = tools
        self.files = files
        self.jobs = [(t, f) for t in tools for f in files if t.can_handle(f)]
        shuffle(self.jobs)

    def __len__(self):
        return len(self.jobs)
