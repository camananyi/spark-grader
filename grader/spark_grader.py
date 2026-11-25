"""SPARK grader: runs a student's Python file against an assignment's checks.

Works the same in the browser (Pyodide) and in regular Python, so checks can be
tested on any computer. A checks file uses: check, Failure, run, source, tree, comments.
"""
import ast
import builtins
import contextlib
import io
import re
import sys
import tokenize
import traceback

STEP_LIMIT = 2_000_000  # lines a student program may run before we call it an infinite loop


class Failure(Exception):
    """Raise inside a check to fail it: Failure("what went wrong", help="how to fix it")."""

    def __init__(self, rationale, help=None):
        super().__init__(rationale)
        self.rationale = rationale
        self.help = help


class _OutOfInput(Exception):
    pass


class _TooManySteps(Exception):
    pass


class Result:
    """What happened when the student's program ran."""

    def __init__(self, output, error=None, line=None):
        self.output = output
        self.error = error  # None when the program finished normally
        self.line = line

    @property
    def crashed(self):
        return self.error is not None


_state = {"source": "", "filename": "", "checks": []}


def source():
    return _state["source"]


def tree():
    return ast.parse(_state["source"])


def comments():
    tokens = tokenize.generate_tokens(io.StringIO(_state["source"]).readline)
    return [t.string for t in tokens if t.type == tokenize.COMMENT]


def check(*depends):
    """Mark a function as a check. Its docstring is what the student sees."""

    def deco(fn):
        _state["checks"].append({"fn": fn, "depends": [d.__name__ for d in depends]})
        return fn

    return deco


def run(inputs=()):
    """Run the student's program, typing each item of inputs when it calls input()."""
    queue = [str(x) for x in inputs]
    out = io.StringIO()
    filename = _state["filename"]

    def fake_input(prompt=""):
        out.write(str(prompt))
        if not queue:
            raise _OutOfInput()
        return queue.pop(0)

    steps = [0]

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != filename:
            return None
        return local

    def local(frame, event, arg):
        if event == "line":
            steps[0] += 1
            if steps[0] > STEP_LIMIT:
                raise _TooManySteps()
        return local

    student_builtins = dict(vars(builtins))
    student_builtins["input"] = fake_input
    env = {"__name__": "__main__", "__builtins__": student_builtins}
    error = line = None
    try:
        code = compile(_state["source"], filename, "exec")
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            sys.settrace(tracer)
            try:
                exec(code, env)
            finally:
                sys.settrace(None)
    except _OutOfInput:
        error = "your program asked for more input than this assignment gives it"
    except _TooManySteps:
        error = "your program ran for too long (is there a loop that never ends?)"
    except SystemExit as e:
        if e.code not in (None, 0):
            error = f"your program stopped with exit({e.code!r})"
    except SyntaxError as e:
        error, line = f"SyntaxError: {e.msg}", e.lineno
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        for frame in reversed(traceback.extract_tb(e.__traceback__)):
            if frame.filename == filename:
                line = frame.lineno
                break
    return Result(out.getvalue(), error, line)


def grade(filename, student_source, checks_source):
    """Run every check and return the results, in order."""
    _state.update(source=student_source, filename=filename, checks=[])
    namespace = {"__name__": "spark_checks"}
    exec(compile(checks_source, "checks", "exec"), namespace)

    results, passed = [], {}
    for item in _state["checks"]:
        fn = item["fn"]
        entry = {"name": fn.__name__, "description": (fn.__doc__ or fn.__name__).strip(),
                 "passed": None, "note": "", "help": ""}
        if not all(passed.get(d) for d in item["depends"]):
            entry["note"] = "not checked yet, fix the earlier problems first"
        else:
            try:
                fn()
                entry["passed"] = True
            except Failure as f:
                entry.update(passed=False, note=f.rationale or "", help=f.help or "")
            except Exception as e:  # a bug in the checks, not the student's fault
                entry.update(passed=False, note=f"the grader had a problem with this check ({type(e).__name__})",
                             help="This one isn't your fault. Tell a mentor.")
        passed[fn.__name__] = entry["passed"] is True
        results.append(entry)
    return results


def crash_message(result, file):
    # Problems the grader found itself read best as they are, with their own hint
    if result.error.startswith("your program ran for too long"):
        return Failure(result.error, help="Look for a while loop whose condition never becomes False.")
    if result.error.startswith("your program asked for more input"):
        return Failure(result.error, help="Check that you ask exactly the questions the assignment lists, no extra ones.")
    if result.error.startswith("your program stopped"):
        return Failure(result.error, help="Take out the exit() so your program can finish normally.")
    where = f" on line {result.line}" if result.line else ""
    return Failure(f"your program crashed{where}: {result.error}",
                   help=f"Run {file} yourself in VS Code and read the last line of the red error message.")
