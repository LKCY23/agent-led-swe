"""Verify native activation from CLI-generated evidence, never model self-report."""
import json


def verify_activation(agent, evidence, source, entrypoint, capture_relative='capture'):
    expected = source is not None
    records = []
    if agent == 'claude-code':
        trace_path = evidence / capture_relative / 'trace.json'
        trace = json.loads(trace_path.read_text())
        init = trace.get('init_context', [])
        discovered = len(init) == 1 and 'agent-led-swe' in init[0].get('skills', [])
        invoked = trace.get('native_skill_invocations', []) == ['agent-led-swe']
        valid = len(init) == 1 and trace.get('isolation_status') == 'verified-discovery' and (
            (discovered and invoked) if expected else not discovered and not trace.get('native_skill_invocations'))
        records = [str(trace_path.relative_to(evidence))]
    else:
        found = False
        body = (source / 'SKILL.md').read_text() if expected else None
        for path in sorted((evidence / 'native-codex-session').rglob('*.jsonl')):
            records.append(str(path.relative_to(evidence)))
            for line in path.read_text().splitlines():
                event = json.loads(line)
                payload = event.get('payload', {})
                if event.get('type') != 'response_item' or payload.get('role') != 'user':
                    continue
                for block in payload.get('content', []):
                    text = block.get('text', '')
                    if text.startswith('<skill>\n<name>agent-led-swe</name>'):
                        if expected and (f'<path>{entrypoint}</path>' not in text or body not in text):
                            return {'status': 'failed', 'reason': 'Injected skill differs from frozen source', 'evidence': records}
                        found = True
        valid = bool(records) and found == expected
    return {'mode': 'native', 'expected': expected, 'status': 'verified' if valid else 'failed',
            'evidence': records}
