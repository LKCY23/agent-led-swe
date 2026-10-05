"""The runner-facing contract; adapters neither prepare tasks nor grade outputs."""
from typing import Protocol


class AgentAdapter(Protocol):
    name: str
    executable: str
    npm_package: str
    cli_entrypoint: str

    def prepare_context(self, binary, workspace, evidence, model, effort, sandbox): ...

    def command(self, binary, workspace, model, effort, sandbox, context): ...

    def inspect_trace(self, text, helpers): ...
