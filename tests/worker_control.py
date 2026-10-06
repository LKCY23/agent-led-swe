"""Stop owned containers at the experiment deadline, before collecting artifacts."""
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
from threading import Event, Timer, RLock


def docker(*args):
    # This is a control-plane timeout, not a generation or development budget.
    return subprocess.check_output(['docker', *args], text=True, stderr=subprocess.PIPE, timeout=30).strip()


def stop_container(name):
    state = json.loads(docker('inspect', '--format', '{{json .State}}', name))
    if state['Running']:
        try:
            if state.get('Paused'):
                docker('unpause', name)
            docker('kill', name)
            docker('wait', name)
        except subprocess.CalledProcessError:
            # A nested user deadline or natural exit may already have stopped it.
            if json.loads(docker('inspect', '--format', '{{json .State}}', name))['Running']:
                raise
    state = json.loads(docker('inspect', '--format', '{{json .State}}', name))
    if state['Running']:
        raise RuntimeError('Owned container did not stop')
    return state


class WorkerCommand(list):
    """An argv with its owned container handles; adapters still consume a list."""
    def __init__(self, argv, container, gateway, evidence):
        super().__init__(argv)
        self.container, self.gateway, self.evidence = container, gateway, Path(evidence)
        self.lock = RLock()

    def stop(self):
        with self.lock:
            self._stop()

    def _stop(self):
        peak_file = self.evidence / 'memory-peak.json'
        if not peak_file.exists():
            try:
                peak = subprocess.check_output(['docker', 'exec', self.container, 'cat',
                    '/sys/fs/cgroup/memory.peak'], text=True, stderr=subprocess.PIPE, timeout=2)
                receipt = {'bytes': int(peak), 'source': 'cgroup-v2 memory.peak'}
            except (OSError, ValueError, subprocess.SubprocessError):
                receipt = {'bytes': None, 'reason': 'Container stopped or cgroup peak unavailable'}
            peak_file.write_text(json.dumps(receipt) + '\n')
        state = stop_container(self.container)
        (self.evidence / 'worker-stop.json').write_text(json.dumps(state, indent=2) + '\n')


@contextmanager
def execution_deadline(commands, seconds):
    workers = [c for c in commands if isinstance(c, WorkerCommand)]
    expired, finished = Event(), Event()
    failures = []

    def stop():
        expired.set()
        try:
            for worker in workers:
                try:
                    worker.stop()
                except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
                    failures.append(str(exc))
                    (worker.evidence / 'workspace-export-error.json').write_text(
                        json.dumps({'error': 'Could not stop worker before snapshot'}))
            for gateway in {w.gateway for w in workers}:
                try:
                    stop_container(gateway)
                except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
                    failures.append(str(exc))
        finally:
            finished.set()

    def check():
        if expired.is_set():
            finished.wait()
            if failures:
                raise RuntimeError('Deadline cleanup failed: ' + '; '.join(failures))
            raise TimeoutError('Shared execution deadline reached; owned workers and gateways stopped')

    timer = Timer(seconds, stop) if workers else None
    if timer:
        timer.daemon = True
        timer.start()
    try:
        yield check
    finally:
        if timer:
            timer.cancel()
            timer.join()
        check()


@contextmanager
def stable_workspace(command):
    """Pause background writers only while copying a turn's public snapshot."""
    if not isinstance(command, WorkerCommand):
        yield
        return
    # Deadline cleanup must not unpause background writers during the copy.
    with command.lock:
        state = json.loads(docker('inspect', '--format', '{{json .State}}', command.container))
        paused_here = state['Running'] and not state.get('Paused')
        if paused_here:
            docker('pause', command.container)
        try:
            yield
        finally:
            state = json.loads(docker('inspect', '--format', '{{json .State}}', command.container))
            if paused_here and state['Running'] and state.get('Paused'):
                docker('unpause', command.container)
