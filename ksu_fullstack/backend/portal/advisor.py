"""The AI adviser.

Design rule: the *rules engine* decides, the adviser only explains. Every answer is
built from the student's own records and carries the rule codes it relied on, so the
student (and staff) can see why. When a question is outside what the records can
answer, the adviser says so and points to a human instead of guessing.

If ANTHROPIC_API_KEY is set, the facts are passed to Claude purely to phrase the reply
more naturally; any failure falls back to the template answer.
"""
import json
import re
import urllib.request

from django.conf import settings

from . import services
from .models import Unit

UNIT_RE = re.compile(r"\b([A-Za-z]{3})\s?-?(\d{3})\b")

HUMAN = "For anything outside your records, please speak to your HOD or the registry office."


def _units_in(student, text):
    found = []
    for a, b in UNIT_RE.findall(text):
        unit = Unit.objects.filter(university=student.program.university, code__iexact=f"{a} {b}").first()
        if unit and unit not in found:
            found.append(unit)
    return found


def _registration_answer(student, units):
    state = services.student_state(student)
    lines, cites, action = [], [], None
    for unit in units:
        issues = services.registration_issues(student, unit, state, include_profile=True)
        blocking = [i for i in issues if i.blocking]
        cites += [i.code for i in issues]
        if not blocking:
            lines.append(f"You can register for {unit.code} ({unit.title}).")
            continue
        lines.append(f"You cannot register for {unit.code} yet: " + " ".join(i.message for i in blocking))
        if any(i.code == "PREREQ_MISSING" for i in blocking) and action is None:
            action = {
                "type": "request_waiver",
                "unit_id": unit.id,
                "label": f"Ask the HOD to waive the prerequisite for {unit.code}",
            }
    return lines, cites, action


def _facts(student, question):
    """Return (answer_text, citations, escalate, suggested_action)."""
    q = question.lower()
    units = _units_in(student, question)

    if units:
        lines, cites, action = _registration_answer(student, units)
        if action:
            lines.append("A prerequisite waiver is a human decision; I can send the request to your HOD.")
        return " ".join(lines), sorted(set(cites)), False, action

    if re.search(r"graduat|clear|finish|degree|credits", q):
        g = services.graduation_for(student)
        text = f"You have {g['passed_credits']} of {g['required_credits']} credits ({g['progress_percent']}%)."
        if g["issues"]:
            text += " " + " ".join(i["message"] for i in g["issues"])
        else:
            text += " You meet every graduation requirement on record."
        return text, sorted({i["code"] for i in g["issues"]}), False, None

    if re.search(r"fee|pay|balance|owe", q):
        bal = float(student.fees_balance)
        if bal > 0:
            return f"Your fee balance is KES {bal:,.0f}. It must be cleared before you can register.", ["FEES_OUTSTANDING"], False, None
        return "Your fees are cleared. No holds on your account.", [], False, None

    if re.search(r"result|mark|gpa|grade|transcript", q):
        state = services.student_state(student)
        text = f"Your GPA is {state['gpa']} across {state['credits']} passed credits." if state["gpa"] is not None else "No results are captured yet."
        held = [c for c, s in state["statuses"].items() if s != "complete"]
        if held:
            text += " Results not final for: " + ", ".join(sorted(held)) + ". Staff or your lecturer must complete or justify these."
        return text, [], False, None

    return "I can answer questions about registering for a unit, fees, results and graduation. " + HUMAN, [], True, None


def _phrase_with_llm(question, facts):
    """Optional. Returns None on any problem so the caller falls back to `facts`."""
    key = getattr(settings, "ANTHROPIC_API_KEY", "")
    if not key:
        return None
    body = {
        "model": getattr(settings, "ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        "max_tokens": 300,
        "system": (
            "You are a university academic adviser. Rewrite the FACTS as a short, friendly answer to the "
            "student's question. Use only the facts given. Do not add rules, dates or promises, and never "
            "say an exception will be granted; exceptions are decided by the HOD."
        ),
        "messages": [{"role": "user", "content": f"Question: {question}\n\nFACTS: {facts}"}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.load(resp)["content"][0]["text"].strip() or None
    except Exception:
        return None


def answer(student, question):
    text, cites, escalate, action = _facts(student, question)
    final = _phrase_with_llm(question, text) or text
    return {"answer": final, "citations": cites, "escalate": escalate, "suggested_action": action}

