"""
HTTP routes.

The web layer: parses requests, calls the domain, renders responses. It holds no
business logic of its own — anything that decides something belongs in
vpsim.domain (ADR-0009).

NOTE (BUILD_PLAN T-030): these server-rendered routes are the prototype. They are
replaced by a JSON API under /v1 once the Next.js client exists (ADR-0006). The
admin console keeps server rendering.
"""

import uuid

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from vpsim.domain.assessment.bias import detect_all_biases
from vpsim.domain.assessment.clinical import evaluate_clinical
from vpsim.domain.content.cases import (
    MASTER_EXAMINATIONS,
    MASTER_INVESTIGATIONS,
    get_all_cases,
    get_case,
)
from vpsim.domain.session import (
    create_session,
    get_session_summary,
    record_exam,
    record_investigation,
    update_session,
)
from vpsim.infra.clock import utc_now_iso
from vpsim.infra.feedback import generate_feedback
from vpsim.infra.llm.gateway import call_llm
from vpsim.infra.session_store import SESSION_STORE
from vpsim.infra.storage import save_session_file

bp = Blueprint("web", __name__)


# ── Menus, grouped once at import ─────────────────────────────────────
# Insertion order (Python 3.7+) preserves the group order declared in
# MASTER_INVESTIGATIONS / MASTER_EXAMINATIONS.

def _group_by(master: dict) -> dict:
    grouped: dict = {}
    for key, item in master.items():
        grouped.setdefault(item["group"], {})[key] = item
    return grouped


_GROUPED_INVESTIGATIONS = _group_by(MASTER_INVESTIGATIONS)
_GROUPED_EXAMINATIONS = _group_by(MASTER_EXAMINATIONS)


@bp.route("/")
def index():
    """Home page — case selection."""
    cases = get_all_cases()
    return render_template("index.html", cases=cases)


@bp.route("/pre_case/<case_id>", methods=["GET"])
def pre_case_get(case_id):
    """Pre-consultation questionnaire page."""
    case = get_case(case_id)
    if not case:
        return redirect(url_for(".index"))
    return render_template("pre_case.html", case=case)


@bp.route("/pre_case/<case_id>", methods=["POST"])
def pre_case_post(case_id):
    """Save pre-case form data, then redirect into the consultation."""
    case = get_case(case_id)
    if not case:
        return redirect(url_for(".index"))

    # Create server-side session now (so pre_case data is associated with it)
    session_id = str(uuid.uuid4())
    session_data = create_session(case_id, started_at=utc_now_iso())

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


@bp.route("/start/<case_id>")
def start_case(case_id):
    """
    Direct start (bypasses pre-case form).
    Used by the 'Try this case again' button on the feedback page.
    """
    case = get_case(case_id)
    if not case:
        return "Case not found.", 404

    session_id = str(uuid.uuid4())
    session_data = create_session(case_id, started_at=utc_now_iso())

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


@bp.route("/chat", methods=["POST"])
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
        patient_reply = call_llm(
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


@bp.route("/examine", methods=["POST"])
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


@bp.route("/investigate", methods=["POST"])
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


@bp.route("/conclude", methods=["POST"])
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
    session_data["end_time"] = utc_now_iso()

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
    save_session_file(
        session_id, case_id, case, session_data,
        store.get("pre_case_data", {}),
        bias_results, clinical_eval, feedback_messages
    )

    return jsonify({"status": "ok"})


@bp.route("/feedback")
def feedback():
    """
    Renders the dedicated feedback page from stored session data.
    """
    session_id = session.get("session_id")
    if not session_id or session_id not in SESSION_STORE:
        return redirect(url_for(".index"))

    store = SESSION_STORE[session_id]
    feedback_data = store.get("feedback_data")
    if not feedback_data:
        return redirect(url_for(".index"))

    return render_template("feedback.html", data=feedback_data)


@bp.route("/save_session", methods=["POST"])
def save_session_route():
    """Thin wrapper — sessions are saved automatically inside /conclude."""
    return jsonify({"status": "Sessions are saved automatically on /conclude."})
