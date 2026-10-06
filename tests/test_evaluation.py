"""Exercise paired execution and grading with local fake CLIs, never an LLM."""
import json
from contextlib import contextmanager
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import evaluate_results
import evaluation_runtime as runtime
import run_evaluation


class EvaluationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.target = self.root / 'target'
        (self.target / 'tests').mkdir(parents=True)
        (self.target / 'SKILL.md').write_text('Frozen skill guidance')
        (self.target / 'tests/rubrics.md').write_text('Use the task agreement.')
        self.case = {'id': 'T1', 'request': 'Write result.txt with the value done.',
                     'files': {'input.txt': 'Input'}, 'acceptance': ['GRADER_ONLY: result is done']}
        self.cli_file = self.root / 'fake-codex'
        self.cli_file.write_text(f'#!{sys.executable}\n' + '''
import json
from pathlib import Path
import sys
import os
args = sys.argv[1:]
workspace = Path(args[args.index('-C') + 1])
prompt = sys.stdin.read()
if 'debug' in args:
    skill = Path(os.environ['HOME']) / '.agents/skills/agent-led-swe/SKILL.md'
    text = '- `r0` = "unused"'
    if skill.exists():
        text = '- `r0` = `' + str(skill.parent.parent) + '`\\n- agent-led-swe (file: r0/agent-led-swe/SKILL.md)'
    print(json.dumps([{'content':[{'text':text}]}]) if skill.exists() else '[]')
    sys.exit(0)
print(json.dumps({'type': 'turn.started'}), flush=True)
if '--output-schema' in args:
    raise AssertionError('Verification must not invoke a model judge')
else:
    assert args[args.index('--sandbox') + 1] == 'workspace-write'
    assert 'GRADER_ONLY' not in prompt
    assert sorted(p.name for p in workspace.iterdir()) == ['input.txt']
    (workspace / 'result.txt').write_text('done')
    session = Path(os.environ['CODEX_HOME']) / 'sessions/probe.jsonl'
    session.parent.mkdir(exist_ok=True)
    skill = Path(os.environ['HOME']) / '.agents/skills/agent-led-swe/SKILL.md'
    text = ('<skill>\\n<name>agent-led-swe</name>\\n<path>' + str(skill) + '</path>\\n' + skill.read_text() + '\\n</skill>') if skill.exists() else prompt
    session.write_text(json.dumps({'type':'response_item','payload':{'type':'message','role':'user','content':[{'text':text}]}})+'\\n')
print(json.dumps({'type': 'turn.completed', 'usage': {
    'input_tokens': 8, 'cached_input_tokens': 0, 'output_tokens': 3}}))
''')
        self.cli_file.chmod(0o700)
        self.cli = {'path': str(self.cli_file), 'version': 'synthetic', 'resolved_path': str(self.cli_file)}
        self.bundle = self.root / 'bundle'

    def run_pair(self):
        with patch.object(run_evaluation, 'ROOT', self.target):
            return run_evaluation.run_pair(self.case, self.bundle, self.cli, 'synthetic',
                                           'low', 5, 1, runtime.DEFAULT_EVALUATOR)

    def test_full_pair_with_no_configured_verifier(self):
        plan = self.run_pair()
        self.assertEqual(plan['max_executor_calls'], 2)
        self.assertEqual(plan['baseline_isolation']['status'], 'unknown')
        commands = []
        for trial in plan['trials']:
            evidence = self.bundle / trial['id']
            record = json.loads((evidence / 'capture/capture.json').read_text())
            commands.append(record['cwd'])
            result = json.loads((evidence / 'result.json').read_text())
            self.assertEqual(result['run_status'], 'completed')
            self.assertEqual(result['usage']['input_tokens'], 8)
            self.assertEqual(result['fixture_before'], {'input.txt': runtime.digest(evidence / 'before/input.txt')})
            prompt = (evidence / 'prompt.txt').read_text()
            self.assertEqual(prompt.startswith('$agent-led-swe\n'), trial['variant'] == 'skill')
        self.assertNotEqual(*commands)
        (self.target / 'SKILL.md').write_text('Later edit')
        self.assertEqual((self.bundle / 'skill/SKILL.md').read_text(), 'Frozen skill guidance')
        review = self.bundle / 'review'
        results = evaluate_results.evaluate_bundle(self.bundle, review)
        self.assertEqual([r['task_status'] for r in results], ['unknown', 'unknown'])
        summary = json.loads((review / 'summary.json').read_text())
        self.assertTrue(summary['pairs'][0]['fixtures_match'])
        self.assertEqual(summary['score_source'], 'task_verifier')
        self.assertEqual(summary['execution_counts'], {'completed': 2})
        with self.assertRaises(FileExistsError):
            self.run_pair()  # No silent overwrite or retry.

    def test_claude_pair_uses_native_adapter(self):
        from model_config import load_profile, CONFIGS
        profile = load_profile(CONFIGS / 'models/deepseek-v4.1-flash.json')
        fake = self.root / 'fake-claude'
        fake.write_text(f'#!{sys.executable}\n' + '''
import json, sys
from pathlib import Path
prompt = sys.stdin.read()
assert 'GRADER_ONLY' not in prompt
Path('result.txt').write_text('done')
print(json.dumps({'type':'system','subtype':'init','tools':['Read'],
                  'skills':['agent-led-swe'] if '/agent-led-swe' in prompt else [],'plugins':[],'mcp_servers':[],'agents':[]}))
if '/agent-led-swe' in prompt:
    print(json.dumps({'type':'user','isReplay':True,'message':{'content':'<command-name>/agent-led-swe</command-name>'}}))
print(json.dumps({'type':'result','subtype':'success','is_error':False,
                  'modelUsage':{'deepseek-flash[1m]':{}},
                  'usage':{'input_tokens':8,'cache_read_input_tokens':0,
                           'cache_creation_input_tokens':0,'output_tokens':3}}))
''')
        fake.chmod(0o700)
        prepare = run_evaluation.prepare_task

        def docker_task(case, output):
            task = prepare(case, output)
            task['environment'] = {'kind': 'docker', 'image': 'synthetic'}
            return task

        @contextmanager
        def environment(task, workspace, evidence, cli, skill, **kwargs):
            yield ['docker', 'exec', 'fake-container', 'claude'], Path('/testbed'), 'danger-full-access', (
                '/opt/target-skill/SKILL.md' if skill else None)

        def execute(helpers, workspace, evidence, command, timeout, prompt, adapter):
            self.assertNotIn('--bare', command)
            self.assertIn('deepseek-flash[1m]', command)
            return runtime.execute(helpers, workspace, evidence, [str(fake)], timeout, prompt, adapter)

        with (patch.object(run_evaluation, 'ROOT', self.target),
              patch.object(run_evaluation, 'prepare_task', side_effect=docker_task),
              patch.object(run_evaluation, 'build_worker_image', return_value='synthetic-worker'),
              patch.object(run_evaluation, 'execution_environment', side_effect=environment),
              patch.object(run_evaluation, 'execute', side_effect=execute),
              patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'synthetic-key'})):
            plan = run_evaluation.run_pair(self.case, self.bundle,
                {'agent': 'claude-code', 'version': '2.1.278'}, 'deepseek-flash', 'high',
                5, 1, runtime.DEFAULT_EVALUATOR, profile)
        self.assertEqual(plan['agent'], 'claude-code')
        for trial in plan['trials']:
            result = json.loads((self.bundle / trial['id'] / 'result.json').read_text())
            self.assertEqual(result['run_status'], 'completed')
            self.assertEqual(result['isolation']['status'], 'verified-discovery')
        results = evaluate_results.evaluate_bundle(self.bundle, self.bundle / 'review')
        self.assertTrue(all(r['task_status'] == 'unknown' for r in results))

    def test_explicit_versions_are_frozen_and_reviewed_with_one_baseline(self):
        candidate = self.root / 'candidate'
        candidate.mkdir()
        (candidate / 'SKILL.md').write_text('Candidate guidance')
        reference = self.root / 'reference'
        reference.mkdir()
        (reference / 'SKILL.md').write_text('Current guidance')
        with patch.object(run_evaluation, 'ROOT', self.target):
            plan = run_evaluation.run_pair(self.case, self.bundle, self.cli, 'synthetic', 'low',
                5, 1, runtime.DEFAULT_EVALUATOR, skill_path=candidate,
                reference_skill_path=reference, reverse_order=True)
        self.assertEqual([t['variant'] for t in plan['trials']], ['candidate', 'current', 'baseline'])
        self.assertEqual((self.bundle / 'skill/SKILL.md').read_text(), 'Candidate guidance')
        self.assertEqual((self.bundle / 'reference-skill/SKILL.md').read_text(), 'Current guidance')
        (candidate / 'SKILL.md').write_text('Unrelated later edit')
        results = evaluate_results.evaluate_bundle(self.bundle, self.bundle / 'review')
        summary = json.loads((self.bundle / 'review/summary.json').read_text())
        self.assertEqual(set(summary['task_counts']), {'baseline', 'current', 'candidate'})
        self.assertTrue(summary['pairs'][0]['fixtures_match'])
        self.assertTrue(all(r['task_status'] == 'unknown' for r in results))
        (self.bundle / 'reference-skill/SKILL.md').write_text('Tampered snapshot')
        with self.assertRaisesRegex(ValueError, 'Frozen skill snapshot changed'):
            evaluate_results.check_bundle(self.bundle, plan)

    def test_current_candidate_only_preserves_native_loading_and_fixture_comparison(self):
        candidate = self.root / 'candidate'
        candidate.mkdir()
        (candidate / 'SKILL.md').write_text('Candidate guidance')
        with patch.object(run_evaluation, 'ROOT', self.target):
            plan = run_evaluation.run_pair(self.case, self.bundle, self.cli, 'synthetic', 'low',
                5, 1, runtime.DEFAULT_EVALUATOR, skill_path=candidate,
                reference_skill_path=self.target, include_baseline=False)
        self.assertEqual([t['variant'] for t in plan['trials']], ['current', 'candidate'])
        self.assertEqual(plan['max_executor_calls'], 2)
        self.assertFalse((self.bundle / 'T1-1-baseline').exists())
        results = evaluate_results.evaluate_bundle(self.bundle, self.bundle / 'review')
        self.assertTrue(all(r['skill_activation']['status'] == 'verified' for r in results))
        pair = evaluate_results.compare(plan, results)['pairs'][0]
        self.assertTrue(pair['comparison_eligible'])
        results[1]['fixture_before'] = {'different.txt': 'different'}
        pair = evaluate_results.compare(plan, results)['pairs'][0]
        self.assertFalse(pair['fixtures_match'])
        self.assertFalse(pair['comparison_eligible'])

    def test_omitting_baseline_requires_reference_before_preparation(self):
        with self.assertRaisesRegex(ValueError, 'requires a reference skill'):
            run_evaluation.run_pair(self.case, self.bundle, self.cli, 'synthetic', 'low',
                5, 1, runtime.DEFAULT_EVALUATOR, skill_path=self.target, include_baseline=False)
        self.assertFalse(self.bundle.exists())

    def test_invalid_skill_path_stops_before_task_preparation(self):
        with self.assertRaisesRegex(ValueError, 'entrypoint not found'):
            run_evaluation.run_pair(self.case, self.bundle, self.cli, 'synthetic', 'low',
                5, 1, runtime.DEFAULT_EVALUATOR, skill_path=self.root / 'missing')
        self.assertFalse(self.bundle.exists())

    def test_timeout_and_zero_exit_without_completion_are_not_passes(self):
        helpers = self.root / 'helpers'
        runtime.freeze_helpers(runtime.DEFAULT_EVALUATOR, helpers)
        workspace = self.root / 'work'
        workspace.mkdir()
        prompt = self.root / 'prompt'
        prompt.write_text('Input')
        timeout = runtime.execute(helpers, workspace, self.root / 'timeout',
                                  [sys.executable, '-c', 'import time; time.sleep(5)'], 0.05, prompt)
        self.assertEqual(timeout['run_status'], 'timeout')
        self.assertIsNone(timeout['usage']['input_tokens'])
        empty = runtime.execute(helpers, workspace, self.root / 'empty',
                                [sys.executable, '-c', 'pass'], 5, prompt)
        self.assertEqual(empty['run_status'], 'error')
        pass_check = [{'status': 'pass'}]
        self.assertEqual(evaluate_results.task_status([]), 'unknown')
        self.assertEqual(evaluate_results.task_status([{'status': 'fail'}]), 'fail')


    def test_missing_trial_stays_in_summary(self):
        plan = self.run_pair()
        missing = self.bundle / plan['trials'][1]['id'] / 'result.json'
        missing.unlink()
        results = evaluate_results.evaluate_bundle(self.bundle, self.bundle / 'review')
        summary = json.loads((self.bundle / 'review/summary.json').read_text())
        self.assertEqual(summary['planned_trials'], 2)
        self.assertEqual(summary['execution_counts']['not_started'], 1)
        self.assertEqual(results[1]['task_status'], 'unknown')

    def test_changed_evidence_is_rejected(self):
        plan = self.run_pair()
        log = self.bundle / plan['trials'][0]['id'] / 'capture/stdout.log'
        original = log.read_text()
        log.write_text('Changed log')
        with self.assertRaisesRegex(ValueError, 'Captured log changed'):
            evaluate_results.evaluate_bundle(self.bundle, self.bundle / 'review-log')
        log.write_text(original)
        (self.bundle / plan['trials'][0]['id'] / 'after/result.txt').write_text('Changed')
        with self.assertRaisesRegex(ValueError, 'Captured artifact changed'):
            evaluate_results.evaluate_bundle(self.bundle, self.bundle / 'review')


    def test_execution_failure_is_preserved_without_dropping_other_variant(self):
        original = runtime.execute
        calls = 0

        def fail_first(*args):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError('Synthetic launch failure')
            return original(*args)

        with patch.object(run_evaluation, 'execute', side_effect=fail_first):
            plan = self.run_pair()
        rows = [json.loads((self.bundle / t['id'] / 'result.json').read_text()) for t in plan['trials']]
        self.assertEqual([r['run_status'] for r in rows], ['error', 'completed'])
        self.assertIn('Synthetic launch failure', rows[0]['error'])
        self.assertTrue((self.bundle / plan['trials'][0]['id'] / 'after/input.txt').exists())

    def test_finalization_failure_is_not_a_completed_submission(self):
        original = runtime.execution_environment

        @contextmanager
        def failed_export(*args, **kwargs):
            with original(*args, **kwargs) as context:
                yield context
            raise RuntimeError('Synthetic artifact export failure')

        with patch.object(run_evaluation, 'execution_environment', side_effect=failed_export):
            plan = self.run_pair()
        self.enable_fixture_verifier()
        with patch.object(evaluate_results, 'validate_task', side_effect=AssertionError('Incomplete artifact')):
            rows = evaluate_results.evaluate_bundle(self.bundle, self.bundle / 'verification')
        self.assertTrue(all(r['run_status'] == 'error' and r['task_status'] == 'unknown' for r in rows))
        self.assertTrue((self.bundle / plan['trials'][0]['id'] / 'capture/stdout.log').exists())

    def test_invalid_budgets(self):
        for value in ('0', '-1', 'nan', 'inf'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                runtime.positive_seconds(value)

    def enable_fixture_verifier(self):
        path = self.bundle / 'case.json'
        case = json.loads(path.read_text())
        case['validation'] = {'kind': 'fixture'}
        runtime.write_json(path, case)
        plan_path = self.bundle / 'plan.json'
        plan = json.loads(plan_path.read_text())
        plan['case_sha256'] = runtime.digest(path)
        runtime.write_json(plan_path, plan)

    def test_verifier_alone_decides_outcome_despite_analysis_or_invalid_activation(self):
        plan = self.run_pair()
        self.enable_fixture_verifier()
        for trial in plan['trials']:
            path = self.bundle / trial['id'] / 'result.json'
            row = json.loads(path.read_text())
            row.update(task_status='fail', checks=[{'status': 'fail'}],
                       skill_activation={'status': 'failed'})
            runtime.write_json(path, row)
        def fixture_check(task, bundle, artifacts, output):
            return [{'id': 'content', 'status': 'pass' if (artifacts / 'result.txt').read_text() == 'done' else 'fail',
                     'reason': 'Actual submitted fixture content', 'evidence': ['after/result.txt']}]
        with patch.object(evaluate_results, 'validate_task', side_effect=fixture_check) as verifier:
            rows = evaluate_results.evaluate_bundle(self.bundle, self.bundle / 'verification')
        self.assertEqual(verifier.call_count, 2)
        self.assertTrue(all(r['task_status'] == 'pass' for r in rows))
        self.assertTrue(all(r['comparison_validity']['status'] == 'invalid' for r in rows))
        self.assertTrue(all('checks' not in r and 'judge' not in r for r in rows))

    def test_verifier_failure_and_unknown_are_preserved(self):
        self.run_pair()
        self.enable_fixture_verifier()
        for status in ('fail', 'unknown'):
            with patch.object(evaluate_results, 'validate_task', return_value=[{'id': 'check', 'status': status}]):
                rows = evaluate_results.evaluate_bundle(self.bundle, self.bundle / status)
            self.assertTrue(all(r['task_status'] == status for r in rows))

    def test_incomplete_execution_does_not_become_a_task_failure(self):
        plan = self.run_pair()
        self.enable_fixture_verifier()
        for trial in plan['trials']:
            path = self.bundle / trial['id'] / 'result.json'
            row = json.loads(path.read_text()); row['run_status'] = 'timeout'
            runtime.write_json(path, row)
        with patch.object(evaluate_results, 'validate_task', side_effect=AssertionError('No completed submission')):
            rows = evaluate_results.evaluate_bundle(self.bundle, self.bundle / 'verification')
        self.assertTrue(all(r['task_status'] == 'unknown' and r['verifier']['state'] == 'not_run' for r in rows))


    def test_context_check_rejects_unparsed_skill_instructions(self):
        from subprocess import CompletedProcess
        response = json.dumps([{'content': [{'text': '<skills_instructions>unexpected</skills_instructions>'}]}])
        with patch.object(runtime.subprocess, 'run', return_value=CompletedProcess([], 0, response, '')):
            with self.assertRaisesRegex(ValueError, 'Unexpected inherited'):
                runtime.isolated_context('codex', self.root, self.root, 'synthetic', 'low', 'read-only')

    def test_context_check_disables_discovered_paths_and_verifies_again(self):
        from subprocess import CompletedProcess
        catalog = '<skills_instructions>\n- `r0` = `/tmp/skills`\n- sample (file: r0/sample/SKILL.md)\n</skills_instructions>'
        responses = [CompletedProcess([], 0, json.dumps([{'content': [{'text': catalog}]}]), ''),
                     CompletedProcess([], 0, '[]', '')]
        with patch.object(runtime.subprocess, 'run', side_effect=responses) as run:
            receipt = runtime.isolated_context('codex', self.root, self.root, 'synthetic', 'low', 'read-only')
        self.assertEqual(receipt['disabled_paths'], ['/tmp/skills/sample/SKILL.md'])
        self.assertEqual(receipt['status'], 'verified-discovery')
        self.assertIn('skills.config=[{path="/tmp/skills/sample/SKILL.md",enabled=false}]',
                      run.call_args_list[1].args[0])


if __name__ == '__main__':
    unittest.main()
