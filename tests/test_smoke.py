from __future__ import annotations

import subprocess
import unittest


class SmokeTests(unittest.TestCase):
    def test_cli_generation_and_validation(self) -> None:
        proc = subprocess.run(
            ["python3", "src/main.py", "--assumptions", "assumptions.yml", "--skip-export"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)
        self.assertIn("Validation summary", proc.stdout)
        self.assertIn('"fk_violations": 0', proc.stdout)
        self.assertIn('"date_logic_violations": 0', proc.stdout)
        self.assertIn('"invoice_math_violations": 0', proc.stdout)
        self.assertIn('"capacity_violations": 0', proc.stdout)


if __name__ == "__main__":
    unittest.main()
