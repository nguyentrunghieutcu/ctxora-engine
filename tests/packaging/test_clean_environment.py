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
                    "distribution = m.distribution('ctxora-engine'); "
                    "files = {str(path) for path in distribution.files}; "
                    "scripts = {entry.name for entry in distribution.entry_points}; "
                    "print(json.dumps({'version': m.version('ctxora-engine'), "
                    "'module': importlib.util.find_spec('harness_context') is not None, "
                    "'canonical': 'harness_context/artifacts/canonical/agents/ctxora-planner.md' "
                    "in files, "
                    "'manifest': 'harness_context/artifacts/manifests/artifacts.json' in files, "
                    "'schema': 'harness_context/artifacts/schemas/artifact-manifest.schema.json' "
                    "in files, "
                    "'interfaces': 'harness_context/interfaces/cli/app.py' in files and "
                    "'harness_context/interfaces/mcp/server.py' in files, "
                    "'infrastructure': "
                    "'harness_context/infrastructure/retrieval/embeddings.py' in files, "
                    "'legacy_shims': 'retrieval/embeddings.py' in files and "
                    "'harness_context/cli/app.py' in files, "
                    "'scripts': sorted(scripts)}))",
                ],
                cwd=temporary,
                check=True,
                capture_output=True,
                text=True,
            )
            installed = json.loads(probe.stdout)
            self.assertEqual(installed["version"], "6.5.5")
            self.assertTrue(installed["module"])
            self.assertTrue(installed["canonical"])
            self.assertTrue(installed["manifest"])
            self.assertTrue(installed["schema"])
            self.assertTrue(installed["interfaces"])
            self.assertTrue(installed["infrastructure"])
            self.assertTrue(installed["legacy_shims"])
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
