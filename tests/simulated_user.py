"""Simulated user hosted by native Claude Code, with an isolated read-only view.

Claude Code owns model calls, built-in tools, session state and structured output.
This adapter only supplies task context, refreshes snapshots and checks receipts.
"""
from contextlib import ExitStack
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from uuid import UUID

from agent_adapters import get_adapter
from agent_adapters.claude_code import BUNDLED_SKILLS
from collaboration_runtime import UserReply
from evaluation_runtime import (DEFAULT_EVALUATOR, execution_environment, file_hashes,
                                freeze_helpers, load_helper, snapshot, write_json)
from model_config import validate_compatibility
from worker_control import execution_deadline

REPLY_SCHEMA = {"type": "object", "properties": {
    "reply": {"type": "string"}, "accepted": {"type": "boolean"}},
    "required": ["reply", "accepted"], "additionalProperties": False}
USER_TOOLS = {"Read", "Glob", "Grep", "StructuredOutput"}


def user_command(binary, cwd, model, effort, system, session_id=None):
    command = get_adapter("claude-code").conversation_command(
        binary, cwd, model, effort, "danger-full-access", {}, session_id)
    command[command.index("--tools") + 1] = "Read,Glob,Grep"
    command[command.index("--permission-mode") + 1] = "dontAsk"
    return command + ["--allowedTools", "Read,Glob,Grep,StructuredOutput",
        "--system-prompt", system, "--json-schema", json.dumps(REPLY_SCHEMA)]


def parse_reply(raw, model, previous_session=None):
    events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    initial = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
    results = [e for e in events if e.get("type") == "result"]
    if len(initial) != 1 or len(results) != 1:
        raise ValueError("Missing native initialization or final result")
    init, final = initial[0], results[0]
    if (any(init.get(k) != [] for k in ("plugins", "mcp_servers"))
            or not isinstance(init.get("skills"), list) or not set(init["skills"]) <= BUNDLED_SKILLS):
        raise ValueError("User instance loaded unexpected skills, plugins or MCP servers")
    if not isinstance(init.get("tools"), list) or set(init["tools"]) != USER_TOOLS:
        raise ValueError("Native user tools must be Read, Glob, Grep and StructuredOutput")
    models = {m.removesuffix("[1m]") for m in (final.get("modelUsage") or {})}
    if models != {model}:
        raise ValueError("Native user model differs from the frozen profile")
    session = str(UUID(final["session_id"]))
    if init.get("session_id") != session or (previous_session and session != previous_session):
        raise ValueError("Native user session changed unexpectedly")
    if final.get("subtype") != "success" or final.get("is_error") is not False:
        raise ValueError("Native user turn did not complete successfully")
    value = final.get("structured_output")
    if not isinstance(value, dict) or set(value) != {"reply", "accepted"}:
        raise ValueError("Native structured_output is missing or invalid")
    reply = UserReply(value["reply"], value["accepted"])
    for event in events:
        content = (event.get("message") or {}).get("content", [])
        for block in content if isinstance(content, list) else []:
            if block.get("type") == "tool_use":
                if block.get("name") not in USER_TOOLS:
                    raise ValueError("User instance attempted an unexpected tool")
    # Whether the review supports acceptance is assessed from the full history,
    # not reduced to a mandatory tool call in this particular turn.
    return reply, session, final


class SimulatedUser:
    def __init__(self, profile, persona, requirements, initial, evidence, environment, cli, credentials,
                 *, effort="high", authenticate=True, model_upstream=None):
        validate_compatibility("claude-code", profile, effort)
        self.profile, self.evidence, self.initial = profile, Path(evidence), Path(initial)
        self.environment = {**environment, "readonly_workspace": True, "install_argv": [], "workspace_mode": "bind", "workdir": "/testbed"}
        self.cli = {**cli, "agent": "claude-code"}
        self.credentials, self.authenticate, self.model_upstream = credentials, authenticate, model_upstream
        self.effort = effort
        self.calls, self.session, self.seen_messages = 0, None, 0
        self.system = persona + "\n\n# 固定任务要求\n" + requirements + (
            "\n\n你是需求提出者，不是负责实现的开发 Agent。通过 Claude Code 原生结构化输出返回 reply 和 accepted。"
            "当前公开产物在 /testbed/current，初始源码在 /testbed/initial。它们只读；"
            "每轮 current 会更新，审阅时读取当前文件，不以旧读到的内容代替。只在需要核查产物时使用工具。")

    def __enter__(self):
        self.stack = ExitStack()
        try:
            self.evidence.mkdir(parents=True, exist_ok=False)
            freeze_helpers(DEFAULT_EVALUATOR, self.evidence / "helpers")
            self.work = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix="native-user-"))).resolve()
            snapshot(self.initial, self.work / "initial")
            (self.work / "current").mkdir()
            self.binary, self.cwd, _, _ = self.stack.enter_context(execution_environment(
                {"environment": self.environment}, self.work, self.evidence, self.cli,
                model_profile=self.profile, credentials=self.credentials, authenticate=self.authenticate,
                model_upstream=self.model_upstream))
            # Verify Docker enforces read-only access, independently of tool policy.
            container = self.binary[self.binary.index("--user") + 2]
            probe = subprocess.run(["docker", "exec", container, "python3", "-c",
                "from pathlib import Path; Path('/testbed/write-probe').write_text('unexpected')"], capture_output=True)
            write_json(self.evidence / "readonly-check.json", {"exit_code": probe.returncode,
                "stderr": probe.stderr.decode(errors="replace")})
            if probe.returncode == 0 or b"Read-only file system" not in probe.stderr:
                raise RuntimeError("User workspace did not enforce a read-only mount")
            return self
        except BaseException:
            self.stack.close()
            raise

    def __exit__(self, *args):
        return self.stack.__exit__(*args)

    def __call__(self, conversation, current, timeout):
        for path in Path(current).rglob("*"):
            if path.is_symlink() and not path.resolve().is_relative_to(Path(current).resolve()):
                raise ValueError("Public snapshot contains an escaping symlink")
        shutil.rmtree(self.work / "current")
        snapshot(current, self.work / "current")
        before = file_hashes(self.work)
        self.calls += 1
        turn = self.evidence / f"reply-{self.calls:03d}"
        turn.mkdir()
        # The user keeps a native session; send only newly observed public messages.
        messages = conversation[self.seen_messages:]
        prompt = turn / "input.jsonl"
        content = "以下是新增的公开对话，请以需求提出者身份回应最后一条开发 Agent 消息。\n" + json.dumps(messages, ensure_ascii=False)
        prompt.write_text(json.dumps({"type": "user", "message": {"role": "user", "content": content}}, ensure_ascii=False) + "\n")
        command = user_command(self.binary, self.cwd, self.profile["model"], self.effort,
                               self.system, self.session)
        capture = load_helper(self.evidence / "helpers/capture.py").capture
        with execution_deadline([self.binary], timeout):
            record = capture(self.work, turn / "capture", command, timeout, prompt)
        if record["timed_out"]:
            raise TimeoutError("Native user turn timed out")
        if record["exit_code"] != 0 or record["launch_error"]:
            raise RuntimeError("Native user CLI failed; see retained capture")
        reply, self.session, final = parse_reply((turn / "capture/stdout.log").read_text(), self.profile["model"], self.session)
        if file_hashes(self.work) != before:
            raise RuntimeError("Native user modified the read-only public view")
        self.seen_messages = len(conversation)
        write_json(turn / "result.json", {"reply": reply.text, "accepted": reply.accepted,
            "session_id": self.session, "native_usage": final.get("usage"), "model_usage": final.get("modelUsage"),
            "artifact_readonly": True})
        return reply
