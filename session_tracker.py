"""
session_tracker.py
------------------
Tracks everything the user does during one consultation session.
Records: questions asked, topics covered, question count, diagnosis.

Called by: app.py on every POST /chat request
Uses: TOPIC_KEYWORDS dictionary for topic detection
Returns: updated session dict stored server-side in SESSION_STORE
"""

from datetime import datetime


# ── Topic keyword lookup table ──────────────────────────────────────
# Maps topic category names to lists of trigger words.
# Category names must match the required_topics lists in cases.py.
# When a user message contains any keyword from a category,
# that topic is marked as covered in the session.
# Matching is case-insensitive substring matching.

TOPIC_KEYWORDS = {
    # ── Case 1: GERD / Chest pain ──────────────────────────────────
    "pain_character": [
        "burning", "crushing", "sharp", "dull", "aching",
        "character", "describe", "feel like", "what kind",
        "pressure", "tight", "stabbing", "squeezing",
        "what does it feel", "type of pain",
    ],
    "meal_relationship": [
        "meal", "food", "eating", "after eating", "diet",
        "drink", "spicy", "coffee", "fasting", "empty stomach",
        "before eating", "after food", "when you eat", "trigger food",
    ],
    "radiation": [
        "radiate", "spread", "arm", "jaw", "shoulder",
        "neck", "anywhere else", "go to", "move to",
        "travels", "down the", "into your",
    ],
    "associated_symptoms": [
        "breathless", "nausea", "sweat", "dizzy", "fever",
        "vomit", "other symptoms", "anything else", "weakness",
        "fatigue", "other problems", "shortness of breath",
    ],
    "medications": [
        "medication", "medicine", "drug", "tablet", "pill",
        "taking", "prescribed", "supplements", "painkillers",
        "regular", "daily", "what do you take", "any pills",
    ],
    "family_history": [
        "family", "father", "mother", "parent", "sibling",
        "hereditary", "runs in family", "relative",
        "grandfather", "grandmother", "anyone in family",
    ],
    "duration_pattern": [
        "how long", "when did", "since when", "started",
        "days", "weeks", "months", "constant", "comes and goes",
        "pattern", "how often", "when does it",
    ],
    "relieving_factors": [
        "better", "worse", "relief", "helps", "aggravate",
        "trigger", "lying down", "sitting up", "activity",
        "rest", "position", "makes it", "alleviate",
    ],

    # ── Case 2: Hypertension / Headache ───────────────────────────
    "headache_character": [
        "throbbing", "pressure", "tight", "band", "one side",
        "both sides", "where", "location", "pulsating",
        "pounding", "headache feel like", "describe headache",
    ],
    "timing_pattern": [
        "morning", "night", "evening", "after", "before",
        "always", "sometimes", "pattern", "when", "how long",
        "duration", "time of day", "worse when",
    ],
    "visual_symptoms": [
        "vision", "blurry", "blur", "spots", "floaters",
        "see", "eyes", "visual", "aura", "light",
        "sensitivity to light", "sight", "seeing",
    ],
    "BP_awareness": [
        "blood pressure", "bp", "checked", "measured",
        "monitor", "high pressure", "reading", "hypertension",
        "pressure ever checked", "blood pressure before",
    ],
    "lifestyle": [
        "sleep", "diet", "water", "hydration", "caffeine",
        "coffee", "alcohol", "exercise", "routine", "lifestyle",
        "habits", "work life", "screen",
    ],
    "stress_assessment": [
        "stress", "pressure", "deadline", "event", "recently",
        "changed", "happened", "difficult", "problem",
        "worry", "anxious", "stressful", "trigger the",
    ],

    # ── Case 3: UTI/Delirium / Elderly confusion ───────────────────
    "onset_timing": [
        "when", "how long", "started", "sudden", "gradual",
        "yesterday", "this morning", "last week", "always",
        "recent", "how quickly", "onset",
    ],
    "baseline_cognition": [
        "normal", "usual", "before", "last week", "always like this",
        "change", "different", "baseline", "normally", "was he",
        "was she", "used to be", "sharp", "always been",
    ],
    "fever": [
        "fever", "temperature", "hot", "chills", "sweating",
        "warm", "shivering", "unwell", "sick",
        "thermometer", "how hot", "temperature check",
    ],
    "urinary_symptoms": [
        "urinate", "urine", "pee", "toilet", "frequency",
        "burning", "colour", "smell", "waterworks",
        "going more", "going less", "painful urination",
        "wee", "urinary", "passing water",
    ],
    "recent_illness": [
        "recently", "fell", "hospital", "unwell", "sick",
        "illness", "injury", "change", "last few days",
        "any recent", "been ill", "before this",
    ],
    "focal_neuro_signs": [
        "weakness", "arm", "leg", "face", "drooping", "speech",
        "slurred", "one side", "movement", "paralysis",
        "can he move", "arms move", "face look",
        "facial", "limb", "motor",
    ],
    "hydration": [
        "eating", "drinking", "water", "fluid", "appetite",
        "dehydrated", "thirsty", "hungry",
        "drinking enough", "how much water", "oral intake",
    ],

    # ── Case 4: Hypothyroidism / Fatigue ──────────────────────────
    "mood_vs_physical": [
        "mood", "sad", "hopeless", "happy", "emotional",
        "how do you feel emotionally", "crying", "enjoying",
        "interests", "depression", "anxious", "mentally",
        "psychologically", "feel inside", "feel down",
        "depressed", "low mood",
    ],
    "weight_change_pattern": [
        "appetite", "more", "less",
        "same", "calories", "changed eating", "portion",
        "hungry", "weight going up", "gaining despite",
        "eating habits", "diet changed",
    ],
    "temperature_tolerance": [
        "cold", "temperature", "always cold", "chilly",
        "layers", "warm", "heating", "hot", "intolerant",
        "feel cold", "cold intolerant", "feel warm",
    ],
    "bowel_habits": [
        "bowel", "constipated", "constipation", "toilet",
        "frequency", "going less", "difficulty", "hard",
        "sluggish", "bowel changed", "stool", "opening bowels",
    ],
    "hair_skin_changes": [
        "hair", "falling out", "hair loss", "skin", "dry",
        "brittle", "nails", "rough", "texture", "changed",
        "hair different", "skin feel", "losing hair",
    ],
    "family_thyroid_history": [
        "family", "thyroid", "mother", "father", "sister",
        "relative", "runs in family", "thyroid condition",
        "underactive", "overactive", "levothyroxine",
        "thyroid tablets", "thyroid history",
    ],
    "menstrual_changes": [
        "period", "menstrual", "cycle", "regular", "heavy",
        "irregular", "missed", "monthly", "flow",
        "spotting", "period changed", "time of month",
    ],
    "energy_time_pattern": [
        "morning", "afternoon", "all day", "worse when",
        "better when", "energy level", "when tired",
        "time of day", "energy", "most tired", "wakes up tired",
    ],

    # ── Case 5: Asthma / Wheezing child ───────────────────────────
    "fever_infection_signs": [
        "fever", "temperature", "runny nose", "sore throat",
        "ear", "tonsils", "sick", "ill", "unwell", "hot",
        "infection sign", "cold symptoms", "snotty", "green",
    ],
    "symptom_timing_pattern": [
        "morning", "night", "evening", "worse when",
        "when bad", "timing", "sleeping", "waking", "pattern",
        "time of day", "night time", "early morning",
    ],
    "exercise_trigger": [
        "exercise", "running", "sport", "pe", "playing",
        "after exercise", "active", "breathless", "exertion",
        "physical", "when he runs", "sport trigger", "gym",
    ],
    "cold_air_trigger": [
        "cold air", "outside", "weather", "cold", "winter",
        "wind", "going out", "temperature changes",
        "cold makes", "outside worse", "outdoors",
    ],
    "duration_recurrence": [
        "before", "first time", "happened before", "previous",
        "recurring", "again", "history of", "ever had",
        "come back", "recurrent", "this before", "in the past",
    ],
    "family_atopy_history": [
        "asthma", "allergy", "eczema", "hay fever",
        "atopy", "family", "inhaler", "allergic family",
        "allergic", "atopic",
    ],
    "school_sport_impact": [
        "school", "missing", "pe", "sport", "activity",
        "playing", "limited", "avoiding", "stopped",
        "cannot", "affected school", "keeping up", "impact",
    ],

    # ── Case 2 (PE): travel history + leg/DVT symptoms ────────────
    "travel_history": [
        "flight", "flew", "plane", "airport", "travel", "travelled",
        "holiday", "trip", "abroad", "long journey", "long haul",
        "car journey", "sitting long", "immobile", "immobility",
        "dubai", "recently travel", "bus journey", "train journey",
    ],
    "leg_symptoms": [
        "leg", "calf", "legs", "swelling", "swollen", "dvt",
        "deep vein", "leg pain", "calf pain", "calf swell",
        "leg swell", "clot in leg", "popliteal", "calf ache",
        "leg aching", "tight calf", "leg oedema",
    ],

    # ── Case 5 (DKA): polydipsia/polyuria + weight loss ───────────
    "thirst_polyuria": [
        "thirst", "thirsty", "drinking more", "polydipsia",
        "urinating more", "peeing more", "polyuria", "passing more",
        "going toilet more", "drinking lots", "excess thirst",
        "excessive thirst", "drinking water lots", "waking at night",
        "nocturia", "how much water", "frequency urination",
        "using toilet a lot", "drink a lot",
    ],
    "weight_history": [
        "weight", "lost weight", "losing weight", "weight loss",
        "thinner", "clothes", "lost kg", "weight change",
        "lighter", "heavier", "gaining weight", "weight going",
        "noticed weight",
    ],
}


# ── Functions ────────────────────────────────────────────────────────

def create_session(case_id):
    """
    Creates a fresh session dictionary for a new consultation.
    Called in app.py when user starts a new case via /start/<case_id>.

    Args:
        case_id (str): e.g. "case_1"

    Returns:
        dict: Empty session with all tracking fields initialized.
    """
    return {
        "case_id": case_id,
        "question_count": 0,
        "questions_asked": [],      # list of all user message strings
        "topics_covered": [],       # list of topic names detected so far
        "exams_performed": [],      # list of examination keys performed
        "investigations_ordered": [],  # list of investigation keys ordered
        "early_diagnosis": None,    # if user mentions diagnosis mid-consult
        "diagnosis_submitted": None,  # final diagnosis string from /conclude
        "start_time": datetime.utcnow().isoformat(),
        "end_time": None,
    }


def record_exam(session, exam_key):
    """Records an examination performed (deduplicated). Returns session."""
    if exam_key not in session["exams_performed"]:
        session["exams_performed"].append(exam_key)
    return session


def record_investigation(session, investigation_key):
    """Records an investigation ordered (deduplicated). Returns session."""
    if investigation_key not in session["investigations_ordered"]:
        session["investigations_ordered"].append(investigation_key)
    return session


def update_session(session, user_message):
    """
    Updates session after every user message.
    Increments question count, extracts topics, checks for early diagnosis.

    Args:
        session (dict): Current session dict from server-side store.
        user_message (str): The raw text the user just sent.

    Returns:
        dict: Updated session dict (mutated in place, also returned).
    """
    # Step 1: increment question counter
    session["question_count"] += 1

    # Step 2: add raw message to history
    session["questions_asked"].append(user_message)

    # Step 3: extract topics from this message
    new_topics = extract_topics(user_message)

    # Step 4: add any new topics not already in covered list
    for topic in new_topics:
        if topic not in session["topics_covered"]:
            session["topics_covered"].append(topic)

    # Step 5: check for early diagnosis mention
    early_diagnosis_phrases = [
        "i think it is", "i think this is", "this looks like",
        "probably ", "could be ", "i believe", "my diagnosis",
        "seems like", "this is a case of", "i suspect",
        "it is likely", "most likely",
    ]
    message_lower = user_message.lower()
    if session["early_diagnosis"] is None:
        for phrase in early_diagnosis_phrases:
            if phrase in message_lower:
                session["early_diagnosis"] = user_message
                break

    return session


def extract_topics(user_message):
    """
    Scans a user message for keywords matching clinical topic categories.
    Uses the TOPIC_KEYWORDS dictionary.

    Matching is case-insensitive substring matching. A topic is only
    added once per message even if multiple keywords match it.

    Args:
        user_message (str): Raw text from user.

    Returns:
        list: Topic category names found in the message.
              e.g. ["meal_relationship", "medications"]
    """
    message_lower = user_message.lower()
    covered = []

    for topic_name, keywords in TOPIC_KEYWORDS.items():
        for keyword in keywords:
            if keyword in message_lower:
                covered.append(topic_name)
                break   # only add each topic once even if multiple keywords match

    return covered


def get_session_summary(session, case_config):
    """
    Returns a readable summary dict for the post-session display screen.
    Used to show the user what they covered and missed.

    Args:
        session (dict): Completed session dict.
        case_config (dict): The case definition from cases.py.

    Returns:
        dict: Summary with coverage stats and missed topics.
    """
    required = case_config["required_topics"]
    covered = session["topics_covered"]

    topics_hit = [t for t in required if t in covered]
    topics_missed = [t for t in required if t not in covered]
    coverage_percent = (
        round((len(topics_hit) / len(required)) * 100) if required else 0
    )

    # Calculate time taken
    time_taken = None
    end_time = session.get("end_time")
    start_time = session.get("start_time")
    if end_time and start_time:
        try:
            end_dt = datetime.fromisoformat(end_time)
            start_dt = datetime.fromisoformat(start_time)
            time_taken = int((end_dt - start_dt).total_seconds())
        except Exception:
            time_taken = None

    return {
        "questions_asked": session["question_count"],
        "topics_covered_count": len(topics_hit),
        "topics_required_count": len(required),
        "coverage_percent": coverage_percent,
        "topics_missed": [t.replace("_", " ") for t in topics_missed],
        "exams_performed_count": len(session.get("exams_performed", [])),
        "investigations_ordered_count": len(session.get("investigations_ordered", [])),
        "diagnosis_given": session["diagnosis_submitted"],
        "time_taken_seconds": time_taken,
    }
