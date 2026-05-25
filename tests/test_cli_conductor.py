from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


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


class ConductorInitCliTests(unittest.TestCase):
    def test_conductor_init_creates_scaffold_in_default_location(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            result = run_ccw("conductor", "init", cwd=target)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ccw-code-task", result.stdout)

            scaffold_dir = target / "ccw-code-task"
            self.assertTrue(scaffold_dir.is_dir())
            self.assertTrue((scaffold_dir / "README.md").is_file())
            self.assertTrue((scaffold_dir / "bin" / "run.sh").is_file())

            readme_text = (scaffold_dir / "README.md").read_text(encoding="utf-8")
            self.assertIn("ccw-code-task", readme_text)
            self.assertIn("ccw init", readme_text)
            self.assertIn("ccw index", readme_text)
            self.assertIn("ccw compile", readme_text)
            self.assertIn("ccw session prepare", readme_text)
            self.assertIn("ccw-stack", readme_text)
            self.assertIn("./bin/run.sh", readme_text)

            run_sh_text = (scaffold_dir / "bin" / "run.sh").read_text(encoding="utf-8")
            self.assertIn("ccw init", run_sh_text)
            self.assertIn("ccw index", run_sh_text)
            self.assertIn("ccw compile", run_sh_text)
            self.assertIn("ccw session prepare", run_sh_text)
            self.assertIn("ccw session validate", run_sh_text)
            self.assertIn("ccw-stack", run_sh_text)

    def test_conductor_init_respects_explicit_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            output_dir = workspace / "custom" / "scaffold"
            result = run_ccw("conductor", "init", "--out", str(output_dir), cwd=workspace)

            self.assertEqual(result.returncode, 0, result.stderr)

            scaffold_dir = output_dir / "ccw-code-task"
            self.assertTrue(scaffold_dir.is_dir())
            self.assertTrue((scaffold_dir / "README.md").is_file())
            self.assertTrue((scaffold_dir / "bin" / "run.sh").is_file())

    def test_conductor_init_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir)
            self.assertEqual(run_ccw("conductor", "init", cwd=target).returncode, 0)
            self.assertEqual(run_ccw("conductor", "init", cwd=target).returncode, 0)

            scaffold_dir = target / "ccw-code-task"
            self.assertTrue(scaffold_dir.is_dir())
            self.assertTrue((scaffold_dir / "README.md").is_file())
            self.assertTrue((scaffold_dir / "bin" / "run.sh").is_file())

            readme_text = (scaffold_dir / "README.md").read_text(encoding="utf-8")
            self.assertIn("ccw-code-task", readme_text)


if __name__ == "__main__":
    unittest.main()
