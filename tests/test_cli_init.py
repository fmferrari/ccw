from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ccw.config import DEFAULT_CONFIG, load_config


def run_ccw(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    python_path = str(ROOT / "src")
    env["PYTHONPATH"] = python_path if not env.get("PYTHONPATH") else f"{python_path}{os.pathsep}{env['PYTHONPATH']}"
    return subprocess.run(
        [sys.executable, "-m", "ccw", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
    )


def run_installed_ccw(*args: str, cwd: Path, venv_dir: Path) -> subprocess.CompletedProcess[str]:
    scripts_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
    python = scripts_dir / ("python.exe" if os.name == "nt" else "python")
    ccw = scripts_dir / ("ccw.exe" if os.name == "nt" else "ccw")

    install = subprocess.run(
        [str(python), "-m", "pip", "install", "-e", str(ROOT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert install.returncode == 0, install.stderr

    return subprocess.run(
        [str(ccw), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
    )


class InitCliTests(unittest.TestCase):
    def assert_runtime_layout(self, target: Path) -> None:
        self.assertTrue((target / ".ccw").is_dir())
        self.assertTrue((target / ".ccw" / "compiled").is_dir())
        self.assertTrue((target / ".ccw" / "snapshots").is_dir())
        self.assertTrue((target / ".ccw" / "config.yaml").is_file())
        self.assertFalse((target / ".ccw" / "index.sqlite").exists())

    def test_init_creates_runtime_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            result = run_ccw("init", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_runtime_layout(target)

    def test_init_creates_runtime_layout_for_explicit_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "repo"
            target.mkdir()

            result = run_ccw("init", str(target), cwd=root)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_runtime_layout(target)

    def test_init_is_idempotent_and_preserves_existing_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            first = run_ccw("init", cwd=target)
            config_path = target / ".ccw" / "config.yaml"
            original_config = config_path.read_text(encoding="utf-8")

            second = run_ccw("init", cwd=target)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(config_path.read_text(encoding="utf-8"), original_config)

    def test_init_creates_loadable_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            result = run_ccw("init", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(load_config(target / ".ccw" / "config.yaml"), DEFAULT_CONFIG)

    def test_init_fails_for_invalid_target_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            missing_target = target / "missing-repo"

            result = run_ccw("init", str(missing_target), cwd=target)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Init target does not exist", result.stderr)

    def test_init_fails_for_non_writable_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "repo"
            target.mkdir()
            target.chmod(0o555)

            try:
                result = run_ccw("init", str(target), cwd=root)
            finally:
                target.chmod(0o755)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not writable", result.stderr.lower())

    def test_init_fails_with_stable_error_when_local_state_path_is_a_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            local_state = target / ".ccw"
            local_state.write_text("conflict", encoding="utf-8")

            result = run_ccw("init", cwd=target)

            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.startswith("Error: "))
            self.assertIn("Local state path exists as a file", result.stderr)

    def test_installed_console_entrypoint_bootstraps_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            venv_dir = root / "venv"
            venv.EnvBuilder(with_pip=True).create(venv_dir)
            target = root / "repo"
            target.mkdir()

            result = run_installed_ccw("init", str(target), cwd=root, venv_dir=venv_dir)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_runtime_layout(target)


if __name__ == "__main__":
    unittest.main()
