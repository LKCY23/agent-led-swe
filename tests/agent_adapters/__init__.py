"""Native agent launch and trace adapters; task and grading semantics stay shared."""
from .base import AgentAdapter


def get_adapter(name) -> AgentAdapter:
    if name == 'codex':
        from .codex import CodexAdapter
        return CodexAdapter()
    if name == 'claude-code':
        from .claude_code import ClaudeCodeAdapter
        return ClaudeCodeAdapter()
    raise ValueError(f'Unsupported agent: {name}')
