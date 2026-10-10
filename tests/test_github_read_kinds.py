#!/usr/bin/env python3
"""Every read kind ships a tested example: its command is read-only and its sample passes validate()."""
import importlib.util
import re
import shlex
import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'scripts/super-board-github-read.py'
CONTRACTS = [
    ROOT / 'workflows/super-board-wave.js',
    ROOT / 'scripts/super-board-codex-lane.sh',
    ROOT / 'scripts/super-board-codex-wave.sh',
]


def load_helper():
    spec = importlib.util.spec_from_file_location('helper', HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def validator_kinds(source):
    """Every kind the validator branches on, read from validate() in the helper source."""
    body = source.split('def validate(')[1].split('\ndef ')[0]
    kinds = set(re.findall(r"kind == '([a-z-]+)'", body))
    for group in re.findall(r'kind in \(([^)]*)\)', body):
        kinds.update(re.findall(r"'([a-z-]+)'", group))
    return sorted(kinds)


class ReadKindExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = HELPER.read_text()
        cls.helper = load_helper()

    def test_every_example_passes_its_own_validator(self):
        kinds = getattr(self.helper, 'KINDS', {})
        self.assertTrue(kinds, 'helper has no KINDS example table')
        for kind, ex in kinds.items():
            with self.subTest(kind=kind):
                self.assertTrue(self.helper.read_only(shlex.split(ex['command'])), 'command is not read-only')
                self.helper.validate(ex['sample'], kind, ex.get('meta'))

    def test_every_validator_and_cli_kind_has_an_example(self):
        examples = sorted(getattr(self.helper, 'KINDS', {}))
        self.assertEqual(examples, sorted(getattr(self.helper, 'KIND_CHOICES', [])))
        missing = [k for k in validator_kinds(self.source) if k not in examples]
        self.assertEqual(missing, [])

    def test_detects_new_validator_kind_without_example(self):
        added = self.source.replace("    elif kind == 'object':",
                                    "    elif kind == 'new-kind':\n        pass\n    elif kind == 'object':")
        self.assertIn('new-kind', validator_kinds(added))

    def test_help_kinds_prints_the_table(self):
        run = subprocess.run([sys.executable, str(HELPER), '--help-kinds'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        for kind in getattr(self.helper, 'KIND_CHOICES', []):
            with self.subTest(kind=kind):
                self.assertRegex(run.stdout, rf'--kind {kind} (--meta \S+ )?-- ')


class LaneContractTests(unittest.TestCase):
    def test_contracts_point_to_help_kinds(self):
        for path in CONTRACTS:
            with self.subTest(path=path.name):
                self.assertIn('super-board-github-read.py --help-kinds', path.read_text())

    def test_codex_wave_does_not_prefix_helper_command_with_gh(self):
        text = (ROOT / 'scripts/super-board-codex-wave.sh').read_text()
        self.assertNotRegex(text, r'--kind \w+ -- gh ')


if __name__ == '__main__':
    unittest.main()
