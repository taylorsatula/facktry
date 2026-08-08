"""Phase 10 red tests: common CLI invocations share the live monitor."""

import subprocess
import sys

import pytest

pytestmark = [pytest.mark.cli, pytest.mark.integration, pytest.mark.slow]


@pytest.mark.parametrize("args", [(), ("cli",), ("watch",)])
def test_bare_monitor_aliases_do_not_require_registry_or_run_flags(tmp_path, args):
    result = subprocess.run([sys.executable, "-m", "facktry.cli.main", *args, "--once", "--home", str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0
    assert "no active objective" in (result.stdout + result.stderr).lower()
