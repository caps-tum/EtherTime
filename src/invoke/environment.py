import os
from collections import UserDict
from dataclasses import dataclass

import util


@dataclass
class InvocationEnvironmentVariable:
    name: str
    value: str
    shell_variable_expansion: bool = False
    variable_extended: bool = False
    separator: str = ":"

    def __str__(self):
        formatted = f"{self.name}={self.value}"
        if self.shell_variable_expansion:
            return f'"{formatted}"'
        return f"'{formatted}'"

    def extend(self, appended_value: str, ):
        self.value_as_extension()
        self.value += self.separator + appended_value
        return self

    def value_as_extension(self):
        self.shell_variable_expansion = True
        if not self.variable_extended:
            self.value = f"${self.name}{self.separator}{self.value}"
            self.variable_extended = True
        return self

class InvocationEnvironment(UserDict):

    def __init__(self):
        # By default, we obtain values from the current environment.
        super().__init__(os.environ)

    def as_shell_exports(self):
        """Get the environment as a 'export KEY=VALUE' chain"""
        return util.str_join([f"export {variable}" for variable in self.values()], separator=" && ")

