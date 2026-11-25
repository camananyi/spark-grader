# SPARK Grader

Students drag their `.py` file onto this website. It runs their program against the assignment's checks
**inside their own browser** (no server runs student code), shows `:)` / `:(` with hints, and when they
click **Submit**, sends the results and a copy of their code to the SPARK grading sheet.

## What's in here

| File | What it is | Do you edit it? |
| --- | --- | --- |
| `config.js` | The grading sheet's web app URL | Once, at setup |
| `checks/index.json` | The list of assignments the site accepts | Each new assignment |
| `checks/<assignment>.py` | The checks for one assignment | Each new assignment |
| `index.html`, `app.js`, `worker.js` | The website itself | No |
| `grader/spark_grader.py` | The engine that runs checks | No |
| `tools/test_checks.py` | Try checks on your own computer | No |

## Adding a new assignment

1. Add the checks file, named after the assignment file: `checks/week3_hourglass.py`.
2. Add a line to `checks/index.json`:
   ```json
   {"slug": "week3_hourglass", "title": "Week 3: Hourglass"}
   ```
   (Mind the commas: every line but the last ends with one.)
3. Add its points to the **Points** tab of the grading sheet: one row per check, plus a `mentor` row.
4. Test it with a sample solution:
   ```
   python3 tools/test_checks.py week3_hourglass path/to/week3_hourglass.py
   ```

The site picks up changes as soon as they're published. Students never need to download anything again.

## Writing checks

A checks file is Python. Each check is a function marked with `@check(...)`; its docstring is what students
see, and raising `Failure("what went wrong", help="how to fix it")` gives it a `:(`.

```python
from spark_grader import Failure, check, comments, crash_message, run, tree

@check()
def exists():
    """week3_hourglass.py exists"""

@check(exists)
def runs_without_errors():
    """program runs without any errors"""
    result = run([5])          # types 5 when the program calls input()
    if result.crashed:
        raise crash_message(result, "week3_hourglass.py")
```

- `run(inputs)` runs the student's program and returns `.output` (everything printed) and `.crashed`.
- `tree()` is the program's syntax tree (for checks like "uses the ** operator"); `comments()` lists its comments.
- `@check(other)` only runs when `other` passed; otherwise it shows `:|`.
- Function names must match the **Check** column on the Points tab.
