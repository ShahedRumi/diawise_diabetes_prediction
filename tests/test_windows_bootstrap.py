"""Windows bootstrap integration tests."""
from pathlib import Path
import os
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'run_windows.ps1'


def _powershell(*arguments, env=None):
    return subprocess.run(
        ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', *arguments],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_windows_check_mode_validates_existing_environment():
    result = _powershell('-File', str(SCRIPT), '-Check')

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'Environment is ready' in result.stdout


def test_backup_broken_environment_preserves_directory(tmp_path):
    environment = tmp_path / '.venv'
    environment.mkdir()
    (environment / 'keep.txt').write_text('preserve me', encoding='utf-8')
    process_env = os.environ.copy()
    process_env['DIAWISE_TEST_ENVIRONMENT'] = str(environment)
    command = (
        f". '{SCRIPT}'; "
        "$backup = Backup-BrokenEnvironment -EnvironmentPath $env:DIAWISE_TEST_ENVIRONMENT; "
        "Write-Output $backup"
    )

    result = _powershell('-Command', command, env=process_env)

    assert result.returncode == 0, result.stdout + result.stderr
    backup = Path(result.stdout.strip().splitlines()[-1])
    assert not environment.exists()
    assert (backup / 'keep.txt').read_text(encoding='utf-8') == 'preserve me'
