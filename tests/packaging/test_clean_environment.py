from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]


class CleanEnvironmentPackagingTests(unittest.TestCase):
    def test_install_import_and_uninstall_in_clean_virtual_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            wheelhouse = temporary / "wheelhouse"
            wheelhouse.mkdir()
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "wheel",
                    "--no-deps",
                    "--no-build-isolation",
                    "--wheel-dir",
                    str(wheelhouse),
                    str(ROOT),
                ],
                cwd=temporary,
                check=True,
                capture_output=True,
                text=True,
            )
            wheel = next(wheelhouse.glob("ctxora_engine-*.whl"))
            environment = temporary / "venv"
            subprocess.run(
                [sys.executable, "-m", "venv", str(environment)],
                check=True,
            )
            python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            subprocess.run(
                [str(python), "-m", "pip", "install", "--no-deps", str(wheel)],
                cwd=temporary,
                check=True,
                capture_output=True,
                text=True,
            )
            probe = subprocess.run(
                [
                    str(python),
                    "-c",
                    "import importlib.metadata as m, importlib.util, json; "
                    "scripts = {entry.name for entry in m.distribution('ctxora-engine').entry_points}; "
                    "print(json.dumps({'version': m.version('ctxora-engine'), "
                    "'module': importlib.util.find_spec('harness_context') is not None, "
                    "'scripts': sorted(scripts)}))",
                ],
                cwd=temporary,
                check=True,
                capture_output=True,
                text=True,
            )
            installed = json.loads(probe.stdout)
            self.assertEqual(installed["version"], "6.2.0")
            self.assertTrue(installed["module"])
            self.assertEqual(installed["scripts"], ["ctxora", "ctxora-mcp"])
            subprocess.run(
                [str(python), "-m", "pip", "uninstall", "-y", "ctxora-engine"],
                cwd=temporary,
                check=True,
                capture_output=True,
                text=True,
            )
            missing = subprocess.run(
                [
                    str(python),
                    "-c",
                    "import importlib.util; "
                    "raise SystemExit(importlib.util.find_spec('harness_context') is not None)",
                ],
                cwd=temporary,
            )
            self.assertEqual(missing.returncode, 0)
