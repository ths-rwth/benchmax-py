from dataclasses import dataclass
import logging
import os
import re

from ..results.Result import Result


@dataclass(unsafe_hash=True)
class Tool:
    name: str
    binary: str
    arguments: str

    def __init__(self, command: str, name="Generic"):
        self.name = name

        parts = command.split(" ")

        self.binary = parts[0]

        if not os.path.isabs(self.binary):
            self.binary = os.getcwd() + "/" + self.binary

        if len(parts) > 0:
            self.arguments = " ".join(parts[1:])
        else:
            self.arguments = ""

    def can_handle(self, file: str) -> bool:
        return True

    # Important: the file has to be the last argument in the command
    # so that escaping regex in parse_command_line works
    def get_command_line(self, file: str) -> str:
        return self.binary + " " + self.arguments + " " + file

    def parse_command_line(self, cmd: str) -> str | None:
        pattern = re.compile(re.escape(self.get_command_line("")) + "(.+)")
        m = pattern.match(cmd)
        if m is None:
            return None
        return m.group(1)

    def parse_additional(self, result: Result):
        pass

    def is_executable(self) -> bool:
        # check whether path is existing file
        if not os.path.isfile(self.binary):
            logging.warning(f"The tool {self.binary} does not seem to be a file.")
            return False
        # check whether file is executable
        if not os.access(self.binary, os.X_OK):
            logging.warning(f"The tool {self.binary} is not executable.")
            return False
        return True
