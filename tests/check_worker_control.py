#!/usr/bin/env python3
"""Real Docker deadline/export checks; no model requests or credentials."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import time

from evaluation_runtime import (DEFAULT_EVALUATOR, execution_environment, file_hashes,
                                load_helper, snapshot, write_json)
from model_config import CONFIGS, load_profile
from worker_control import execution_deadline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker-image', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    cli = {'agent': 'claude-code', 'version': json.loads((CONFIGS / 'agents.json').read_text())['claude-code']['version']}
    profile = load_profile(CONFIGS / 'models/deepseek-v4.1-flash.json')
    reports = []
    for mode in ('bind', 'copy'):
        evidence = output / mode
        evidence.mkdir()
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp).resolve()
            (work / 'deleted.txt').write_text('remove during execution')
            task = {'environment': {'kind': 'docker', 'worker_image': args.worker_image,
                    'workspace_mode': mode, 'install_argv': [], 'workspace_excludes': ['cache']}}
            timed_out = False
            with execution_environment(task, work, evidence, cli, authenticate=False,
                    model_profile=profile, model_upstream='http://127.0.0.1:1') as runtime:
                binary = runtime[0]
                child = "from pathlib import Path; import time\np=Path('/testbed/ticks.txt')\nwhile True:\n p.write_text(str(time.time_ns())); time.sleep(.02)"
                script = ("from pathlib import Path; import subprocess,time\n"
                          "Path('/testbed/deleted.txt').unlink(); Path('/testbed/new.md').write_text('new artifact')\n"
                          "Path('/testbed/cache').mkdir(); Path('/testbed/cache/ignored.txt').write_text('dependency')\n"
                          f"subprocess.Popen(['python3','-c',{child!r}]); time.sleep(60)")
                try:
                    with execution_deadline([binary], 2):
                        load_helper(DEFAULT_EVALUATOR / 'scripts/capture.py').capture(work,
                            evidence / 'capture', ['docker', 'exec', binary.container, 'python3', '-c', script], 10)
                except TimeoutError:
                    timed_out = True
                state = json.loads(subprocess.check_output(['docker', 'inspect', '--format', '{{json .State}}', binary.container], text=True))
                write_json(evidence / 'deadline-observation.json', {'timed_out': timed_out,
                    'command_type': type(binary).__name__, 'state': state})
                assert not state['Running'], 'Timeout returned before stopping the worker'
            first = file_hashes(work)
            time.sleep(.15)
            assert first == file_hashes(work), 'Background writer survived cleanup'
            assert (work / 'new.md').read_text() == 'new artifact'
            assert (work / 'ticks.txt').is_file()
            assert not (work / 'deleted.txt').exists()
            if mode == 'copy':
                assert not (work / 'cache').exists(), 'Excluded image data leaked into exported artifact'
            snapshot(work, evidence / 'after')
            resources = json.loads((evidence / 'resource-result.json').read_text())
            assert resources['memory_limit_bytes'] == 3 * 1024 ** 3
            assert resources['nano_cpus'] == 2_000_000_000
            reports.append({'mode': mode, 'passed': timed_out, 'writer_stopped': True,
                            'artifact_stable': True, 'resources': resources})
        write_json(output / 'report.json', {'model_calls': 0, 'cases': reports})
    print(json.dumps(reports))
    return 0 if all(r['passed'] for r in reports) else 1


if __name__ == '__main__':
    raise SystemExit(main())
