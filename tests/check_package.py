#!/usr/bin/env python3
"""Check package metadata and local reference integrity; not model behavior."""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    import yaml

    entry = ROOT / 'SKILL.md'
    text = entry.read_text()
    front = yaml.safe_load(text.split('---', 2)[1])
    manifest = json.loads((ROOT / '.claude-plugin/plugin.json').read_text())
    ui = yaml.safe_load((ROOT / 'agents/openai.yaml').read_text())
    assert front['name'] == ROOT.name == manifest['name'] == 'agent-led-swe'
    assert re.fullmatch(r'\d+\.\d+\.\d+', manifest['version'])
    assert manifest['skills'] == ['./']
    assert ui['policy']['allow_implicit_invocation'] is True
    interface = ui['interface']
    assert 25 <= len(interface['short_description']) <= 64
    assert '$agent-led-swe' in interface['default_prompt']
    assert interface['display_name']

    graph = {}
    for path in ROOT.rglob('*.md'):
        if '.git' in path.parts or 'runs' in path.parts:
            continue
        body = path.read_text()
        assert body.count('```') % 2 == 0, f'Unclosed fence: {path}'
        graph[path] = []
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', body):
            parsed = urlsplit(target)
            if parsed.scheme or not parsed.path:
                continue
            dest = (path.parent / unquote(parsed.path)).resolve()
            assert dest.is_relative_to(ROOT), f'Outside package: {path}: {target}'
            assert dest.is_file(), f'Broken link: {path}: {target}'
            graph[path].append(dest)

    reachable, queue = set(), [entry]
    while queue:
        current = queue.pop()
        if current in reachable:
            continue
        reachable.add(current)
        queue.extend(graph.get(current, []))
    resources = set((ROOT / 'references').rglob('*.md')) | set((ROOT / 'assets/templates').rglob('*.md'))
    assert resources <= reachable, f'Unreachable resources: {resources - reachable}'
    print(json.dumps({'result': 'passed', 'version': manifest['version'],
                      'markdown_files_checked': len(graph),
                      'reachable_resources': len(resources)}, indent=2))


if __name__ == '__main__':
    main()
