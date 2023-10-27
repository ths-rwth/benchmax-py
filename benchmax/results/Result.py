from dataclasses import dataclass, field
from datetime import timedelta


@dataclass
class Result:
    exit_code: int = -1
    runtime: timedelta = field(default_factory=timedelta)
    peak_memory_kbytes: int = 0
    answer: str = "None"
    stdout: str = ""
    stderr: str = ""
    additional_info: dict[str, str] = field(default_factory=dict)
