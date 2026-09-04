import unittest
from pathlib import Path

from harness_context.topology import audit


class PhaseGTopologyTests(unittest.TestCase):
    def test_release_topology_and_oss_independence(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(audit(root), [])
