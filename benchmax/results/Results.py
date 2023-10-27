from dataclasses import dataclass, field

from results.Result import Result
from tools.Tool import Tool


@dataclass
class Results:
    tools: dict[Tool, int] = field(default_factory=dict)
    files: dict[str, int] = field(default_factory=dict)
    data: dict[tuple[int, int], Result] = field(default_factory=dict)

    def get(self, tool: Tool, file: str) -> Result | None:
        tool_id = self.tools.get(tool, None)
        if tool_id is None:
            return None
        file_id = self.files.get(file, None)
        if file_id is None:
            return None
        return self.data.get((tool_id, file_id), None)

    def add_result(self, tool: Tool, file: str, result: Result):
        tool_id = self.tools.setdefault(tool, len(self.tools))
        file_id = self.files.setdefault(file, len(self.files))
        self.data[(tool_id, file_id)] = result

    def size(self):
        return len(self.data)

    def collect_statistics(self) -> set[str]:
        return {s for r in self.data.values() for s in r.additional_info}
