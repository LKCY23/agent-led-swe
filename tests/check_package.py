#!/usr/bin/env python3
"""Check package metadata and local reference integrity; not model behavior."""
from pathlib import Path
from urllib.parse import unquote, urlsplit
from html import unescape
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def markdown_body(path):
    """Return prose outside fenced examples for repository link checks."""
    lines, fence = [], None
    for line in path.read_text().splitlines():
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if fence is not None:
            if (marker and marker[1][0] == fence[0]
                    and len(marker[1]) >= fence[1] and not marker[2].strip()):
                fence = None
        elif marker:
            fence = (marker[1][0], len(marker[1]))
        else:
            lines.append(line)
    assert fence is None, f'Unclosed fence: {path}'
    return '\n'.join(lines)


def heading_anchors(body):
    """Build GitHub-style anchors for the ATX headings used in this repo."""
    anchors = set()
    for title in re.findall(r'^ {0,3}#{1,6}[ \t]+(.+)$', body, re.MULTILINE):
        title = re.sub(r'[ \t]+#+[ \t]*$', '', title).strip()
        title = re.sub(r'!?\[([^\]]+)\]\([^)]+\)', r'\1', title)
        title = re.sub(r'<[^>]+>', '', title)
        slug = re.sub(r'[^\w\- ]', '', unescape(title).lower()).replace(' ', '-')
        anchor, suffix = slug, 0
        while anchor in anchors:
            suffix += 1
            anchor = f'{slug}-{suffix}'
        anchors.add(anchor)
    return anchors


def main():
    import yaml

    entry = ROOT / 'SKILL.md'
    text = entry.read_text()
    front = yaml.safe_load(text.split('---', 2)[1])
    manifest = json.loads((ROOT / '.claude-plugin/plugin.json').read_text())
    ui = yaml.safe_load((ROOT / 'agents/openai.yaml').read_text())
    # A Git worktree may have a different directory name; package identity is metadata.
    assert front['name'] == manifest['name'] == 'agent-led-swe'
    assert re.fullmatch(r'\d+\.\d+\.\d+', manifest['version'])
    assert manifest['skills'] == ['./']
    assert ui['policy']['allow_implicit_invocation'] is True
    interface = ui['interface']
    assert 25 <= len(interface['short_description']) <= 64
    assert '$agent-led-swe' in interface['default_prompt']
    assert interface['display_name']

    graph, fragments_checked, anchors = {}, 0, {}
    for path in ROOT.rglob('*.md'):
        if any(part in path.parts for part in ('.git', '.venv', 'runs', '__pycache__')):
            continue
        body = markdown_body(path)
        graph[path] = []
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', body):
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not (parsed.path or parsed.fragment):
                continue
            dest = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            assert dest.is_relative_to(ROOT), f'Outside package: {path}: {target}'
            assert dest.is_file(), f'Broken link: {path}: {target}'
            if parsed.fragment and dest.suffix.lower() == '.md':
                if dest not in anchors:
                    anchors[dest] = heading_anchors(markdown_body(dest))
                assert unquote(parsed.fragment) in anchors[dest], f'Broken fragment: {path}: {target}'
                fragments_checked += 1
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
                      'fragment_links_checked': fragments_checked,
                      'reachable_resources': len(resources)}, indent=2))


if __name__ == '__main__':
    main()
