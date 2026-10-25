# Regression: ISSUE-001 — README quickstart scanned the source folder, which customers never receive
# Found by /qa on 2026-10-25
# Report: .gstack/qa-reports/qa-report-agent-economy-2026-10-25.md

import contextlib
import io
import os
import pathlib
import re
import shlex
import shutil
import tempfile
import unittest

from dataworth.__main__ import main

ROOT = pathlib.Path(__file__).resolve().parent.parent


class QuickstartRegression(unittest.TestCase):
    def test_every_quickstart_line_works_from_the_release_archive_layout(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        block = re.search(r"## Quickstart\n.*?```bash\n(.*?)```", readme, re.S).group(1)
        lines = [ln for ln in block.splitlines() if ln.strip() and not ln.startswith("pip install")]
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(ROOT / "examples", pathlib.Path(tmp) / "examples")  # all a customer has besides the wheel
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                for line in lines:
                    with self.subTest(line=line):
                        out = io.StringIO()
                        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                            code = main(shlex.split(line)[1:])
                        self.assertEqual(code, 0, f"{line!r} exited {code}")
                        self.assertTrue(out.getvalue().strip())
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
