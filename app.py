"""
app.py
------
Main Flask application. All URL routes for the web app.

Routes:
  GET  /                      → case selection page
  GET  /pre_case/<case_id>    → pre-consultation questionnaire
  POST /pre_case/<case_id>    → save pre-case data, redirect to chat
  GET  /start/<case_id>       → begin consultation (also called from pre_case POST)
  POST /chat                  → user sends message, get patient reply
  POST /conclude              → user submits diagnosis, runs bias detection
  GET  /feedback              → render dedicated feedback page
  POST /save_session          → thin wrapper (auto-saved inside /conclude)

Session storage:
  Flask session cookie holds only session_id.
  Full state lives in SESSION_STORE (in-memory dict keyed by session_id).
  This avoids cookie size limits.

LLM API:
  Uses Groq chat-completions (OpenAI-compatible) via the `groq` library.
  Model set by GROQ_MODEL in .env (default: llama-3.3-70b-versatile).
  Retry logic handles free-tier rate limits automatically.
"""

import os
import json
import time
import uuid
from datetime import datetime

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
from groq import Groq

from cases import get_all_cases, get_case, MASTER_INVESTIGATIONS, MASTER_EXAMINATIONS
from session_tracker import (
    create_session, update_session, get_session_summary,
    record_exam, record_investigation, count_prior_sessions,
)
from bias_detector import detect_all_biases
from clinical_evaluator import evaluate_clinical
from feedback_generator import generate_feedback

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

# Initialize Groq client (OpenAI-compatible chat completions API).
# Model is overridable via GROQ_MODEL in .env without touching code.
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
LLM_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Pre-group MASTER_INVESTIGATIONS for the chat template ─────────────
# Built once at startup; passed to every chat.html render.
# Dict insertion order (Python 3.7+) preserves the group order
# declared in MASTER_INVESTIGATIONS / MASTER_EXAMINATIONS.
_GROUPED_INVESTIGATIONS: dict = {}
for _key, _inv in MASTER_INVESTIGATIONS.items():
    _g = _inv["group"]
    if _g not in _GROUPED_INVESTIGATIONS:
        _GROUPED_INVESTIGATIONS[_g] = {}
    _GROUPED_INVESTIGATIONS[_g][_key] = _inv

_GROUPED_EXAMINATIONS: dict = {}
for _key, _ex in MASTER_EXAMINATIONS.items():
    _g = _ex["group"]
    if _g not in _GROUPED_EXAMINATIONS:
        _GROUPED_EXAMINATIONS[_g] = {}
    _GROUPED_EXAMINATIONS[_g][_key] = _ex


# ── Server-side session store ─────────────────────────────────────────
# Format:
# {
#   session_id: {
#     "session_data":  {...},      # create_session output
#     "conversation":  [...],      # Gemini history
#     "pre_case_data": {...},      # pre-case form answers
#     "feedback_data": {...}       # /conclude output (for /feedback page)
#   }
# }
SESSION_STORE = {}


# ── LLM helper with retry ─────────────────────────────────────────────

def _call_llm(messages, system_instruction, max_tokens=200, temperature=0.7,
              max_retries=3):
    """
    Calls the Groq chat-completions API with retry on transient errors.

    Args:
        messages (list): [{"role": "user"|"assistant", "content": str}, ...]
                         conversation history, oldest first.
        system_instruction (str): system prompt (the patient persona).

    Returns:
        str: the assistant's reply text.

    Raises:
        The last exception if all retries fail.
    """
    payload = [{"role": "system", "content": system_instruction}] + messages

    last_err = None
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                messages=payload,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            text = (resp.choices[0].message.content or "").strip()
            if not text:
                raise ValueError("Empty response from model")
            return text
        except Exception as e:
            last_err = e
            transient = any(s in str(e) for s in
                            ("429", "500", "502", "503", "over capacity",
                             "rate limit", "Empty response"))
            if transient and attempt < max_retries - 1:
                wait = (attempt + 1) * 2   # 2 s, 4 s
                print(f"LLM transient error — retrying in {wait}s "
                      f"(attempt {attempt+1}): {str(e)[:80]}")
                time.sleep(wait)
            else:
                raise
    raise last_err


# ── Routes ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Home page — case selection."""
    cases = get_all_cases()
    return render_template("index.html", cases=cases)


@app.route("/pre_case/<case_id>", methods=["GET"])
def pre_case_get(case_id):
    """Pre-consultation questionnaire page."""
    case = get_case(case_id)
    if not case:
        return redirect(url_for("index"))
    return render_template("pre_case.html", case=case)


@app.route("/pre_case/<case_id>", methods=["POST"])
def pre_case_post(case_id):
    """Save pre-case form data, then redirect into the consultation."""
    case = get_case(case_id)
    if not case:
        return redirect(url_for("index"))

    # Create server-side session now (so pre_case data is associated with it)
    session_id = str(uuid.uuid4())
    session_data = create_session(case_id)

    pre_case_data = {
        "participant_id": request.form.get("participant_id", "").strip(),
        "year_of_study":  request.form.get("year_of_study", ""),
        "confidence":     request.form.get("confidence", ""),
    }

    SESSION_STORE[session_id] = {
        "session_data":  session_data,
        "conversation":  [],
        "pre_case_data": pre_case_data,
        "feedback_data": None,
    }

    session["session_id"] = session_id
    session["case_id"]    = case_id

    return render_template("chat.html", case=case,
                           grouped_investigations=_GROUPED_INVESTIGATIONS,
                           grouped_examinations=_GROUPED_EXAMINATIONS)


@app.route("/start/<case_id>")
def start_case(case_id):
    """
    Direct start (bypasses pre-case form).
    Used by the 'Try this case again' button on the feedback page.
    """
    case = get_case(case_id)
    if not case:
        return "Case not found.", 404

    session_id = str(uuid.uuid4())
    session_data = create_session(case_id)

    SESSION_STORE[session_id] = {
        "session_data":  session_data,
        "conversation":  [],
        "pre_case_data": {},
        "feedback_data": None,
    }

    session["session_id"] = session_id
    session["case_id"]    = case_id

    return render_template("chat.html", case=case,
                           grouped_investigations=_GROUPED_INVESTIGATIONS,
                           grouped_examinations=_GROUPED_EXAMINATIONS)


@app.route("/chat", methods=["POST"])
def chat():
    """
    Receives a user question and returns the virtual patient's reply.
    Updates session tracking on every call.

    Body:   {"message": "Does the pain go to your arm?"}
    Returns: {"response": "No, just in my chest.", "question_count": 3}
    """
    session_id = session.get("session_id")
    case_id    = session.get("case_id")

    if not session_id or session_id not in SESSION_STORE:
        return jsonify({"error": "No active session. Please go back and select a case."}), 400

    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message."}), 400

    store       = SESSION_STORE[session_id]
    session_data = store["session_data"]
    conversation = store["conversation"]
    case        = get_case(case_id)

    # Build chat history in OpenAI/Groq format.
    # Stored roles are "user"/"model"; the API expects "user"/"assistant".
    messages = [
        {
            "role": "user" if msg["role"] == "user" else "assistant",
            "content": msg["content"],
        }
        for msg in conversation
    ]
    messages.append({"role": "user", "content": user_message})

    try:
        patient_reply = _call_llm(
            messages=messages,
            system_instruction=case["system_prompt"],
            max_tokens=200,
            temperature=0.7,
        )

    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "rate limit" in err_str.lower():
            msg = ("The patient is taking a moment — please wait a few seconds "
                   "and try again.")
        else:
            msg = "The patient could not respond right now. Please try again."
        return jsonify({"error": msg}), 500

    # Update tracking and history
    update_session(session_data, user_message)
    conversation.append({"role": "user",  "content": user_message})
    conversation.append({"role": "model", "content": patient_reply})

    return jsonify({
        "response":       patient_reply,
        "question_count": session_data["question_count"],
    })


@app.route("/examine", methods=["POST"])
def examine():
    """
    Performs an examination from the universal MASTER_EXAMINATIONS list.

    If the system is one of this case's KEY/RELEVANT examinations, returns
    the case-specific finding from case["examination"].
    Otherwise returns the generic NORMAL finding from MASTER_EXAMINATIONS —
    so students cannot infer the diagnosis from which systems are available.

    Body:   {"system": "vitals"}
    Returns: {"label": "Vital Signs", "finding": "HR 76 ..."}
    """
    session_id = session.get("session_id")
    case_id    = session.get("case_id")
    if not session_id or session_id not in SESSION_STORE:
        return jsonify({"error": "No active session."}), 400

    data       = request.get_json(silent=True) or {}
    system_key = data.get("system", "")

    # Validate against the master list (not the case-specific list)
    if system_key not in MASTER_EXAMINATIONS:
        return jsonify({"error": "Unknown examination."}), 400

    case      = get_case(case_id)
    case_exam = case.get("examination", {})

    # Case-specific finding if relevant; normal finding otherwise
    if system_key in case_exam:
        finding = case_exam[system_key]["finding"]
    else:
        finding = MASTER_EXAMINATIONS[system_key]["normal_result"]

    # Always use the master label for consistency across cases
    label = MASTER_EXAMINATIONS[system_key]["label"]

    record_exam(SESSION_STORE[session_id]["session_data"], system_key)

    return jsonify({"label": label, "finding": finding})


@app.route("/investigate", methods=["POST"])
def investigate():
    """
    Orders an investigation from the universal MASTER_INVESTIGATIONS list.

    If the test is one of this case's KEY/RELEVANT investigations, returns
    the case-specific (often abnormal) result from case["investigations"].
    Otherwise returns the generic NORMAL result from MASTER_INVESTIGATIONS —
    so students cannot infer the diagnosis from which tests are available.

    Body:   {"test": "ecg"}
    Returns: {"label": "ECG (12-lead)", "result": "Normal sinus rhythm ..."}
    """
    session_id = session.get("session_id")
    case_id    = session.get("case_id")
    if not session_id or session_id not in SESSION_STORE:
        return jsonify({"error": "No active session."}), 400

    data     = request.get_json(silent=True) or {}
    test_key = data.get("test", "")

    # Validate against master list (not the case-specific list)
    if test_key not in MASTER_INVESTIGATIONS:
        return jsonify({"error": "Unknown investigation."}), 400

    case     = get_case(case_id)
    case_inv = case.get("investigations", {})

    # Case-specific result if relevant; normal result otherwise
    if test_key in case_inv:
        result = case_inv[test_key]["result"]
    else:
        result = MASTER_INVESTIGATIONS[test_key]["normal_result"]

    # Always use the master label for consistency across cases
    label = MASTER_INVESTIGATIONS[test_key]["label"]

    record_investigation(SESSION_STORE[session_id]["session_data"], test_key)

    return jsonify({"label": label, "result": result})


@app.route("/conclude", methods=["POST"])
def conclude():
    """
    Receives the student's final diagnosis.
    Runs bias detection, generates Socratic feedback, saves session JSON,
    stores feedback_data in SESSION_STORE for the /feedback page.

    Body:    {"diagnosis": "Myocardial infarction"}
    Returns: 200 OK (body ignored — JS redirects to /feedback)
    """
    session_id = session.get("session_id")
    case_id    = session.get("case_id")

    if not session_id or session_id not in SESSION_STORE:
        return jsonify({"error": "No active session."}), 400

    data      = request.get_json(silent=True) or {}
    diagnosis = data.get("diagnosis", "").strip()
    if not diagnosis:
        return jsonify({"error": "No diagnosis provided."}), 400

    store        = SESSION_STORE[session_id]
    session_data = store["session_data"]
    case         = get_case(case_id)

    # Record diagnosis and end time
    session_data["diagnosis_submitted"] = diagnosis
    session_data["end_time"] = datetime.utcnow().isoformat()

    # Run bias detection (cognitive reasoning)
    bias_results = detect_all_biases(session_data, case)

    # Run clinical evaluation (diagnosis, exams, investigations)
    clinical_eval = evaluate_clinical(session_data, case)

    # Generate feedback (diagnosis-aware, combines both)
    feedback_messages = generate_feedback(
        bias_results, clinical_eval, session_data, case
    )

    # Build session summary
    summary = get_session_summary(session_data, case)

    # Topics hit/missed for the feedback template coverage grid
    required    = case["required_topics"]
    covered     = session_data["topics_covered"]
    topics_hit  = [t for t in required if t in covered]
    topics_missed = [t for t in required if t not in covered]

    # ── Examination Scorecard ─────────────────────────────────────────
    # Categorise every examination the student performed and every key
    # exam they should have done.
    all_exams = session_data.get("exams_performed", [])
    case_exam = case.get("examination", {})

    exam_scorecard = {
        "key_done":      [],   # essential exam performed ✓
        "key_missed":    [],   # essential exam skipped ○
        "relevant_done": [],   # in case dict but not key (fine to do)
        "extra_done":    [],   # from master, not in case dict (not needed)
    }
    for k in all_exams:
        lbl = (MASTER_EXAMINATIONS[k]["label"] if k in MASTER_EXAMINATIONS
               else case_exam.get(k, {}).get("label", k))
        if k in case_exam:
            if case_exam[k].get("key"):
                exam_scorecard["key_done"].append(lbl)
            else:
                exam_scorecard["relevant_done"].append(lbl)
        else:
            exam_scorecard["extra_done"].append(lbl)
    for k, v in case_exam.items():
        if v.get("key") and k not in all_exams:
            lbl = (MASTER_EXAMINATIONS[k]["label"] if k in MASTER_EXAMINATIONS
                   else v.get("label", k))
            exam_scorecard["key_missed"].append(lbl)

    # ── Investigation Scorecard ───────────────────────────────────────
    # Categorise every test ordered and every key test not ordered.
    all_inv  = session_data.get("investigations_ordered", [])
    case_inv = case.get("investigations", {})

    inv_scorecard = {
        "key_done":        [],   # key test ordered ✓
        "key_missed":      [],   # key test not ordered ○
        "reasonable_done": [],   # reasonable test ordered (appropriate)
        "low_value_done":  [],   # low-value test ordered (flagged ⚠)
        "extra_done":      [],   # from master, not in case dict (neutral)
    }
    for k in all_inv:
        lbl = (MASTER_INVESTIGATIONS[k]["label"] if k in MASTER_INVESTIGATIONS
               else case_inv.get(k, {}).get("label", k))
        if k in case_inv:
            cat = case_inv[k].get("category", "")
            if cat == "key":
                inv_scorecard["key_done"].append(lbl)
            elif cat == "reasonable":
                inv_scorecard["reasonable_done"].append(lbl)
            elif cat == "low_value":
                inv_scorecard["low_value_done"].append(lbl)
        else:
            inv_scorecard["extra_done"].append(lbl)
    for k, v in case_inv.items():
        if v.get("category") == "key" and k not in all_inv:
            lbl = (MASTER_INVESTIGATIONS[k]["label"] if k in MASTER_INVESTIGATIONS
                   else v.get("label", k))
            inv_scorecard["key_missed"].append(lbl)

    # Package everything the /feedback template needs
    feedback_data = {
        "case_id":           case_id,
        "case_title":        case["title"],
        "diagnosis_given":   diagnosis,
        "questions_asked":   session_data["question_count"],
        "biases_detected":   bias_results,
        "clinical_eval":     clinical_eval,
        "feedback_messages": feedback_messages,
        "session_summary":   summary,
        "topics_hit":        topics_hit,
        "topics_missed":     topics_missed,
        "exam_scorecard":    exam_scorecard,
        "inv_scorecard":     inv_scorecard,
    }
    store["feedback_data"] = feedback_data

    # Save research data JSON
    _save_session_file(
        session_id, case_id, case, session_data,
        store.get("pre_case_data", {}),
        bias_results, clinical_eval, feedback_messages
    )

    return jsonify({"status": "ok"})


@app.route("/feedback")
def feedback():
    """
    Renders the dedicated feedback page from stored session data.
    """
    session_id = session.get("session_id")
    if not session_id or session_id not in SESSION_STORE:
        return redirect(url_for("index"))

    store = SESSION_STORE[session_id]
    feedback_data = store.get("feedback_data")
    if not feedback_data:
        return redirect(url_for("index"))

    return render_template("feedback.html", data=feedback_data)


@app.route("/save_session", methods=["POST"])
def save_session_route():
    """Thin wrapper — sessions are saved automatically inside /conclude."""
    return jsonify({"status": "Sessions are saved automatically on /conclude."})


# ── Helpers ───────────────────────────────────────────────────────────

def _save_session_file(session_id, case_id, case, session_data,
                       pre_case_data, bias_results, clinical_eval,
                       feedback_messages):
    """
    Saves completed session as JSON in sessions/ folder.
    Includes pre-case questionnaire + clinical evaluation for analysis.
    Silently skips if folder is not writable.
    """
    try:
        os.makedirs("sessions", exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # ── Participant linking (for within-subject pre/post analysis) ────
        # Sequence = how many sessions this participant has already completed,
        # plus one. Computed BEFORE writing this file so it is not counted.
        participant_id = (pre_case_data.get("participant_id", "") or "").strip()
        session_sequence = count_prior_sessions("sessions", participant_id) + 1
        # Filesystem-safe participant id for the filename (falls back to "anon").
        safe_pid = "".join(
            c for c in participant_id if c.isalnum() or c in "-_"
        ) or "anon"

        stem     = f"{safe_pid}_{case_id}_seq{session_sequence}_{timestamp}"
        filename = f"sessions/{stem}.json"

        log = {
            "session_id":       stem,
            "case_id":          case_id,
            "case_title":       case["title"],
            "correct_diagnosis": case["correct_diagnosis"],
            # Pre-case questionnaire data (evaluation metadata)
            "participant": {
                "participant_id":   participant_id,
                "session_sequence": session_sequence,
                "year_of_study":    pre_case_data.get("year_of_study", ""),
                "confidence_pre":   pre_case_data.get("confidence", ""),
            },
            "start_time":       session_data.get("start_time"),
            "end_time":         session_data.get("end_time"),
            "question_count":   session_data["question_count"],
            "questions_asked":  session_data["questions_asked"],
            "topics_covered":   session_data["topics_covered"],
            "exams_performed":  session_data.get("exams_performed", []),
            "investigations_ordered": session_data.get("investigations_ordered", []),
            "early_diagnosis":  session_data.get("early_diagnosis"),
            "diagnosis_submitted": session_data["diagnosis_submitted"],
            "diagnosis_verdict": clinical_eval["diagnosis"]["verdict"],
            "biases_detected":  bias_results,
            "clinical_eval":    clinical_eval,
            "feedback_given":   feedback_messages,
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)

        print(f"Session saved: {filename}")

    except Exception as e:
        print(f"Warning: Could not save session file: {e}")


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)
