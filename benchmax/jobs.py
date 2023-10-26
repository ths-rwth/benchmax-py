from tools.Tool import Tool

class Jobs:
    def __init__(self, tools: list[Tool], files: list[str]):
        self.tools = tools
        self.files = files
        self.jobs = [(t,f) for t in tools for f in files if t.can_handle(f)]


    def __len__(self):
        return len(self.jobs)


    # TODO: randomization
    


