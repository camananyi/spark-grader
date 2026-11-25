"""Week 2: Pennies"""
import ast
import re

from spark_grader import Failure, check, comments, crash_message, run, tree

TITLE = "Week 2: Pennies"
FILE = "week2_pennies.py"
FILLER_COMMENT = re.compile(r"^#\s*(line\s*\d*|code|comment|todo|\d+|stuff|here)?\s*$", re.I)


def answer(pennies, days):
    """The official answer in dollars: the pennies double once per day."""
    return pennies * 2 ** days / 100


def _numbers(out):
    return [float(n) for n in re.findall(r"\d+(?:\.\d+)?", out.replace(",", ""))]


def _check_amount(pennies, days):
    expected = answer(pennies, days)
    result = run([pennies, days])
    if result.crashed:
        raise crash_message(result, FILE)
    nums = _numbers(result.output)
    if any(abs(n - expected) < 0.005 for n in nums):
        return
    hint = "Check your math: how many pennies are there after doubling every day, and how many pennies are in a dollar?"
    if any(abs(n - expected / 2) < 0.005 for n in nums):
        hint = "Your answer is exactly half of the expected one. Check how many times the pennies double."
    elif any(abs(n - expected * 2) < 0.005 for n in nums):
        hint = "Your answer is exactly double the expected one. Check how many times the pennies double."
    elif any(abs(n - expected * 100) < 0.5 for n in nums):
        hint = "That looks like the answer in pennies. Divide by 100 to get dollars."
    what = "1 penny" if pennies == 1 else f"{pennies} pennies"
    raise Failure(f"for {what} over {days} days, expected ${expected:,.2f}", help=hint)


@check()
def exists():
    """week2_pennies.py exists"""


@check(exists)
def compiles():
    """week2_pennies.py has no syntax errors"""
    try:
        tree()
    except SyntaxError as e:
        raise Failure(f"Python couldn't read your file: line {e.lineno}: {e.msg}",
                      help="Check that line for a missing quote, bracket, or colon.")


@check(compiles)
def uses_int_input():
    """asks for the pennies and the days using int(input())"""
    count = sum(1 for n in ast.walk(tree())
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "int"
                and n.args and isinstance(n.args[0], ast.Call)
                and isinstance(n.args[0].func, ast.Name) and n.args[0].func.id == "input")
    if count < 2:
        raise Failure(f"found {count} int(input()) call(s), expected 2",
                      help='Ask both questions like: pennies = int(input("How many pennies? "))')


@check(compiles)
def uses_power_operator():
    """uses the ** operator to calculate the doubling"""
    if not any(isinstance(n, (ast.BinOp, ast.AugAssign)) and isinstance(n.op, ast.Pow) for n in ast.walk(tree())):
        raise Failure("didn't find the ** operator",
                      help="2 ** 3 means 2 x 2 x 2. Use ** to double the pennies once for each day.")


@check(compiles)
def runs_without_errors():
    """program runs without any errors"""
    result = run([1, 30])
    if result.crashed:
        raise crash_message(result, FILE)


@check(runs_without_errors)
def correct_for_example():
    """1 penny over 30 days gives the right total in dollars"""
    _check_amount(1, 30)


@check(runs_without_errors)
def correct_for_other_inputs():
    """gives the right total for other starting pennies and days"""
    for pennies, days in [(3, 10), (7, 20), (5, 3)]:
        _check_amount(pennies, days)


@check(correct_for_example)
def readable_dollars():
    """prints the total as dollars with a $ and two decimal places"""
    expected = answer(5, 3)
    out = run([5, 3]).output.replace(",", "")
    if not re.search(r"\$\s*" + re.escape(f"{expected:.2f}") + r"(?!\d)", out):
        raise Failure(f"for 5 pennies over 3 days, expected to see ${expected:.2f} in your output",
                      help='Put a $ in front and show exactly 2 decimal places, e.g. print(f"${total:.2f}")')


@check(compiles)
def has_comments():
    """has at least 2 meaningful comments"""
    meaningful = [c for c in comments()
                  if not FILLER_COMMENT.match(c) and len(re.findall(r"[A-Za-z]+", c)) >= 3]
    if len(meaningful) < 2:
        raise Failure(f"found {len(meaningful)} meaningful comment(s), expected at least 2",
                      help="Explain what your code does, e.g. # double the pennies once for each day")
