"""Execute the workflow's real gate shell, not a source-pattern surrogate."""
import json
import os
from pathlib import Path
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
JOBS = yaml.safe_load((ROOT / '.github/workflows/ci.yaml').read_text())['jobs']
GATE = JOBS['all-checks-pass']
FLAGS = 'python python_prod frontend site scan deps uv_lock npm_lock installer desktop_updater rust docker_meta mcp_catalog ci_review'.split()
ALWAYS = {'detect', 'infographic-check', 'profile-artifact-check', 'case-collision-check', 'osv-scanner'}
LANES = {'tests': 'python', 'tests-os': 'python', 'lint': 'python', 'contributor-check': 'python', 'js-tests': 'frontend', 'installer-tests': 'installer', 'rust-tests': 'rust', 'docs-site': 'site', 'uv-lockfile': 'uv_lock', 'docker-lint': 'docker_meta'}
REQUIRED = ALWAYS | set(LANES) | {'history-check', 'lockfile-diff', 'supply-chain', 'review-labels'}


def scenario(event='pull_request', enabled=(), critical=''):
    outputs = {key: str(key in enabled).lower() for key in FLAGS}
    outputs['event_name'] = event
    required = ALWAYS | {job for job, flag in LANES.items() if flag in enabled}
    if event == 'pull_request':
        required |= {'history-check'}
        if 'npm_lock' in enabled:
            required.add('lockfile-diff')
        if {'scan', 'deps'} & set(enabled):
            required.add('supply-chain')
        if {'ci_review', 'mcp_catalog'} & set(enabled) or critical == 'true':
            required.add('review-labels')
    needs = {job: {'result': 'success' if job in required else 'skipped', 'outputs': {}} for job in REQUIRED}
    needs['detect']['outputs'] = outputs
    needs['supply-chain']['outputs']['critical_findings'] = critical
    return needs


def evaluate(tmp_path, needs):
    # GitHub provides only direct dependencies to the step's needs context.
    payload = {key: value for key, value in needs.items() if key in GATE['needs']}
    step = next(step for step in GATE['steps'] if step.get('id') == 'evaluate')
    output = tmp_path / 'output'
    env = {'PATH': os.environ['PATH'], 'HOME': str(tmp_path), 'NEEDS': json.dumps(payload), 'GITHUB_OUTPUT': str(output)}
    result = subprocess.run(['/bin/bash', '-e', '-o', 'pipefail', '-c', step['run']], cwd=ROOT, env=env, capture_output=True, text=True)
    return result


@pytest.mark.parametrize('event,enabled,critical', [
    ('pull_request', (), ''), ('push', FLAGS, ''),
    ('pull_request', ('deps',), ''), ('pull_request', ('scan',), 'false'),
    ('pull_request', ('scan',), 'true'), ('pull_request', ('ci_review',), ''),
    ('pull_request', ('mcp_catalog',), ''),
    *[('pull_request', (flag,), 'false' if flag == 'scan' else '') for flag in FLAGS],
])
def test_intentional_skips_follow_real_event_and_dependency_gates(tmp_path, event, enabled, critical):
    result = evaluate(tmp_path, scenario(event, enabled, critical))
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('job', sorted(REQUIRED) + ['output:' + flag for flag in set(LANES.values()) | {'scan', 'deps', 'npm_lock', 'ci_review', 'mcp_catalog', 'event_name'}] + ['critical_findings'])
@pytest.mark.parametrize('bad', ['cancelled', 'failure', 'unknown', '', 'skipped', None])
def test_required_results_fail_closed(tmp_path, job, bad):
    needs = scenario('pull_request', FLAGS, 'true')
    if job.startswith('output:'):
        target, key = needs['detect']['outputs'], job.split(':', 1)[1]
    elif job == 'critical_findings':
        target, key = needs['supply-chain']['outputs'], job
    else:
        target, key = needs, job
    if bad is None:
        del target[key]
    elif target is needs:
        needs[job]['result'] = bad
    else:
        target[key] = bad
    result = evaluate(tmp_path, needs)
    assert result.returncode != 0, f'{job}={bad!r} accepted: {result.stdout}'
