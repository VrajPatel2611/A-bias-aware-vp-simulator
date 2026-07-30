# Pseudocode Document — Bias-Aware Virtual Patient Simulator
# Project: B.Tech Summer Internship 2026 — DA-IICT
# Last updated: Day 3 — May 13, 2026
# Status: LIVING DOCUMENT — update before changing Python files

---

## DOCUMENT PURPOSE

This file contains the complete logic for every module in the project
written as pseudocode before any real Python is written. The rule is:
if you cannot explain the logic clearly in pseudocode, you are not
ready to write the Python. Every function in bias_detector.py,
session_tracker.py, and feedback_generator.py must appear here first.

---

## IMPORTANT: LIBRARY DECISION

We are using google-genai (the NEW Google library) NOT google-generativeai
(the deprecated old library). This affects how every Gemini call is
written throughout the project.

OLD deprecated way (DO NOT USE):
  import google.generativeai as genai
  genai.configure(api_key=...)
  model = genai.GenerativeModel(...)

NEW correct way (USE THIS):
  from google import genai
  from google.genai import types
  client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
  response = client.models.generate_content(
      model="gemini-2.5-flash", ...)

Model to use everywhere: gemini-2.5-flash
Reason: Available on free tier, best instruction-following of the
free models, verified working with our API key.

---

## MODULE 1: session_tracker.py

### Purpose
Records everything the user does during one consultation session.
Called by app.py on every user message. Stores the growing record
in Flask session object between requests.

---

### TOPIC_KEYWORDS Dictionary
This is the shared lookup table used by extract_topics().
It maps topic category names to lists of trigger words.
These category names are the same strings used in required_topics
lists inside cases_design.md and cases.py.

TOPIC_KEYWORDS = {

  "pain_character": [
    "burning", "crushing", "sharp", "dull", "aching",
    "character", "describe", "feel like", "what kind",
    "pressure", "tight", "stabbing", "throbbing pain"
  ],

  "meal_relationship": [
    "meal", "food", "eating", "after eating", "diet",
    "drink", "spicy", "coffee", "fasting", "empty stomach",
    "before eating", "after food", "when you eat"
  ],

  "radiation": [
    "radiate", "spread", "arm", "jaw", "shoulder", "neck",
    "back", "anywhere else", "go to", "move to", "travels"
  ],

  "associated_symptoms": [
    "breathless", "nausea", "sweat", "dizzy", "fever",
    "vomit", "other symptoms", "anything else", "weakness",
    "fatigue", "other problems"
  ],

  "medications": [
    "medication", "medicine", "drug", "tablet", "pill",
    "taking", "prescribed", "supplements", "painkillers",
    "regular", "daily", "what do you take"
  ],

  "family_history": [
    "family", "father", "mother", "parent", "sibling",
    "hereditary", "runs in family", "relative",
    "grandfather", "grandmother", "anyone in family"
  ],

  "duration_pattern": [
    "how long", "when did", "since when", "started",
    "days", "weeks", "months", "constant", "comes and goes",
    "pattern", "always", "sometimes", "when does it"
  ],

  "relieving_factors": [
    "better", "worse", "relief", "helps", "aggravate",
    "trigger", "lying down", "sitting up", "activity",
    "rest", "position", "makes it"
  ],

  "headache_character": [
    "throbbing", "pressure", "tight", "band", "one side",
    "both sides", "where", "location", "describe", "pulsating",
    "pounding", "headache feel like"
  ],

  "timing_pattern": [
    "morning", "night", "evening", "after", "before",
    "always", "sometimes", "pattern", "when", "how long",
    "duration", "time of day", "worse when"
  ],

  "visual_symptoms": [
    "vision", "blurry", "blur", "spots", "floaters",
    "see", "eyes", "visual", "aura", "light",
    "sensitivity to light", "sight"
  ],

  "BP_awareness": [
    "blood pressure", "BP", "checked", "measured",
    "monitor", "high pressure", "reading", "hypertension",
    "pressure ever checked"
  ],

  "lifestyle": [
    "sleep", "diet", "water", "hydration", "caffeine",
    "coffee", "alcohol", "exercise", "routine", "lifestyle",
    "habits", "work life"
  ],

  "stress_assessment": [
    "stress", "pressure", "deadline", "event", "recently",
    "changed", "happened", "difficult", "problem",
    "worry", "anxious", "stressful"
  ],

  "onset_timing": [
    "when", "how long", "started", "sudden", "gradual",
    "yesterday", "this morning", "last week", "always",
    "recent", "how quickly"
  ],

  "baseline_cognition": [
    "normal", "usual", "before", "last week", "always like this",
    "change", "different", "baseline", "normally", "was he",
    "was she", "used to be"
  ],

  "fever": [
    "fever", "temperature", "hot", "chills", "sweating",
    "warm", "cold", "shivering", "unwell", "sick",
    "thermometer", "how hot"
  ],

  "urinary_symptoms": [
    "urinate", "urine", "pee", "toilet", "frequency",
    "burning", "colour", "smell", "waterworks",
    "going more", "less", "painful urination"
  ],

  "recent_illness": [
    "recently", "fell", "hospital", "unwell", "sick",
    "illness", "injury", "change", "last few days",
    "any recent", "been ill"
  ],

  "focal_neuro_signs": [
    "weakness", "arm", "leg", "face", "drooping", "speech",
    "slurred", "one side", "movement", "paralysis",
    "can he move", "arms move", "face look"
  ],

  "hydration": [
    "eating", "drinking", "water", "food", "appetite",
    "fluids", "dehydrated", "thirsty", "hungry",
    "drinking enough", "how much water"
  ],

  "mood_vs_physical": [
    "mood", "sad", "hopeless", "happy", "emotional",
    "how do you feel emotionally", "crying", "enjoying",
    "interests", "depression", "anxious", "mentally",
    "psychologically", "feel inside"
  ],

  "weight_change_pattern": [
    "eating", "food", "appetite", "diet", "more", "less",
    "same", "calories", "changed eating", "portion",
    "hungry", "weight going up", "gaining despite"
  ],

  "temperature_tolerance": [
    "cold", "temperature", "always cold", "chilly",
    "layers", "warm", "heating", "hot", "intolerant",
    "feel cold", "cold intolerant", "feel warm"
  ],

  "bowel_habits": [
    "bowel", "constipated", "constipation", "toilet",
    "frequency", "going less", "difficulty", "hard",
    "sluggish", "bowel changed", "stool"
  ],

  "hair_skin_changes": [
    "hair", "falling out", "hair loss", "skin", "dry",
    "brittle", "nails", "rough", "texture", "changed",
    "hair different", "skin feel"
  ],

  "family_thyroid_history": [
    "family", "thyroid", "mother", "father", "sister",
    "relative", "runs in family", "thyroid condition",
    "underactive", "overactive", "levothyroxine", "thyroid tablets"
  ],

  "menstrual_changes": [
    "period", "menstrual", "cycle", "regular", "heavy",
    "irregular", "missed", "monthly", "flow",
    "spotting", "period changed", "time of month"
  ],

  "energy_time_pattern": [
    "morning", "afternoon", "all day", "worse when",
    "better when", "energy level", "when tired",
    "time of day", "energy", "most tired"
  ],

  "fever_infection_signs": [
    "fever", "temperature", "runny nose", "sore throat",
    "ear", "tonsils", "sick", "ill", "unwell", "hot",
    "infection sign", "cold symptoms"
  ],

  "symptom_timing_pattern": [
    "morning", "night", "evening", "worse when",
    "when bad", "timing", "sleeping", "waking", "pattern",
    "time of day", "night time", "early morning"
  ],

  "exercise_trigger": [
    "exercise", "running", "sport", "PE", "playing",
    "after exercise", "active", "breathless", "exertion",
    "physical", "when he runs", "sport trigger"
  ],

  "cold_air_trigger": [
    "cold air", "outside", "weather", "cold", "winter",
    "wind", "going out", "temperature changes",
    "cold makes", "outside worse"
  ],

  "duration_recurrence": [
    "before", "first time", "happened before", "previous",
    "recurring", "again", "history of", "ever had",
    "come back", "recurrent", "this before"
  ],

  "family_atopy_history": [
    "asthma", "allergy", "eczema", "hay fever",
    "atopy", "family", "mother", "father", "sibling",
    "relative", "inhaler", "allergic family"
  ],

  "school_sport_impact": [
    "school", "missing", "PE", "sport", "activity",
    "playing", "limited", "avoiding", "stopped",
    "cannot", "affected school", "keeping up"
  ]
}

---

### FUNCTION: create_session(case_id)

PURPOSE: Creates a fresh empty session for a new consultation.
Called in app.py when user clicks "Begin Consultation".
Returns a dict stored in Flask session object.

PSEUDOCODE:
FUNCTION create_session(case_id):
  RETURN {
    "case_id": case_id,
    "question_count": 0,
    "questions_asked": [],         # list of all user message strings
    "topics_covered": [],          # list of topic names detected so far
    "early_diagnosis": None,       # if user mentions diagnosis mid-consult
    "diagnosis_submitted": None,   # final diagnosis string from /conclude
    "start_time": current_timestamp,
    "end_time": None
  }

NOTES:
- questions_asked grows by 1 every time user sends a message
- topics_covered grows as new topics are detected
- early_diagnosis is set if user mentions a diagnosis before /conclude
  (detect by checking if message contains words like "I think it is",
  "this looks like", "probably", "could be", "diagnosis is")

---

### FUNCTION: update_session(session, user_message)

PURPOSE: Called on every POST /chat request after getting user message.
Updates question count, extracts topics, checks for early diagnosis.
Returns the updated session dict.

PSEUDOCODE:
FUNCTION update_session(session, user_message):

  # Step 1: increment question counter
  session["question_count"] = session["question_count"] + 1

  # Step 2: add raw message to history
  session["questions_asked"].append(user_message)

  # Step 3: extract topics from this message
  new_topics = extract_topics(user_message)

  # Step 4: add any new topics not already in covered list
  FOR each topic IN new_topics:
    IF topic NOT IN session["topics_covered"]:
      session["topics_covered"].append(topic)

  # Step 5: check for early diagnosis mention
  early_diagnosis_phrases = [
    "i think it is", "i think this is", "this looks like",
    "probably", "could be", "i believe", "my diagnosis",
    "seems like", "this is a case of", "i suspect"
  ]
  message_lower = lowercase(user_message)
  FOR each phrase IN early_diagnosis_phrases:
    IF phrase IN message_lower:
      IF session["early_diagnosis"] IS None:
        session["early_diagnosis"] = user_message
      BREAK

  RETURN session

---

### FUNCTION: extract_topics(user_message)

PURPOSE: Scans one user message for keywords matching clinical topics.
Uses the TOPIC_KEYWORDS dictionary above.
Returns a list of matched topic category names.

PSEUDOCODE:
FUNCTION extract_topics(user_message):
  message_lower = lowercase(user_message)
  covered = empty list

  FOR each topic_name, keywords IN TOPIC_KEYWORDS:
    FOR each keyword IN keywords:
      IF keyword IN message_lower:
        covered.append(topic_name)
        BREAK  # only add each topic once even if multiple keywords match

  RETURN covered

EXAMPLE:
  Input:  "Does the pain get worse after eating anything?"
  Checks: "after eating" is in meal_relationship keywords → MATCH
  Checks: nothing else matches
  Output: ["meal_relationship"]

EXAMPLE 2:
  Input: "Do you take any regular medications or supplements?"
  Checks: "medications" in medications keywords → MATCH
  Checks: "regular" in medications keywords → already matched
  Checks: "supplements" in medications keywords → already matched
  Output: ["medications"]

---

### FUNCTION: get_session_summary(session, case_config)

PURPOSE: Returns a human-readable summary dict used for the
post-session display screen. Called after /conclude.

PSEUDOCODE:
FUNCTION get_session_summary(session, case_config):
  required = case_config["required_topics"]
  covered = session["topics_covered"]

  topics_hit = [t for t in required IF t IN covered]
  topics_missed = [t for t in required IF t NOT IN covered]
  coverage_percent = (len(topics_hit) / len(required)) * 100

  RETURN {
    "questions_asked": session["question_count"],
    "topics_covered_count": len(topics_hit),
    "topics_required_count": len(required),
    "coverage_percent": round(coverage_percent),
    "topics_missed": topics_missed,
    "diagnosis_given": session["diagnosis_submitted"],
    "time_taken_seconds": end_time - start_time
  }

---
---

## MODULE 2: bias_detector.py

### Purpose
Analyses a completed session to detect 3 cognitive biases.
Called by app.py after user submits their diagnosis via /conclude.
Takes the session dict and case_config dict as inputs.
Returns a structured dict of detection results.

---

### FUNCTION: detect_all_biases(session, case_config)

PURPOSE: Main entry point. Runs all 3 detectors and returns combined
results. This is the only function app.py calls directly.

PSEUDOCODE:
FUNCTION detect_all_biases(session, case_config):
  RETURN {
    "anchoring": detect_anchoring(session, case_config),
    "premature_closure": detect_premature_closure(session, case_config),
    "confirmation_bias": detect_confirmation_bias(session, case_config)
  }

EACH detector returns a dict with this exact structure:
{
  "detected": True or False,
  "score": float between 0.0 and 1.0,
  "reason": string explaining why it was detected,
  "evidence": list of specific user questions that triggered it
}

WHY SCORE 0-1 INSTEAD OF TRUE/FALSE:
A binary detected/not-detected gives unfair feedback.
A user who asked 6 of 8 required topics shows MILD premature closure
(score 0.25) — very different from someone who asked 2 of 8 (score 0.75).
The score makes the feedback proportional and fair.

---

### FUNCTION: detect_anchoring(session, case_config)

PURPOSE: Checks if user over-focused on the anchor topic without
exploring alternative explanations.

PSEUDOCODE:
FUNCTION detect_anchoring(session, case_config):

  anchor_keywords = case_config["anchor_keywords"]
  alternative_topics = case_config["alternative_topics"]
  all_questions = session["questions_asked"]
  total_questions = session["question_count"]

  # Count how many questions contained anchor keywords
  anchor_question_count = 0
  anchor_evidence = []

  FOR each question IN all_questions:
    question_lower = lowercase(question)
    FOR each keyword IN anchor_keywords:
      IF keyword IN question_lower:
        anchor_question_count = anchor_question_count + 1
        anchor_evidence.append(question)
        BREAK  # count each question once

  # Count how many questions contained alternative topic words
  alternative_question_count = 0
  FOR each question IN all_questions:
    question_lower = lowercase(question)
    FOR each keyword IN alternative_topics:
      IF keyword IN question_lower:
        alternative_question_count = alternative_question_count + 1
        BREAK

  # RULE A1: Topic concentration
  # If more than 60% of questions were about the anchor topic
  detected_A1 = False
  score_A1 = 0.0
  IF total_questions >= 4:
    concentration = anchor_question_count / total_questions
    IF concentration > 0.60:
      detected_A1 = True
      score_A1 = round(concentration, 2)

  # RULE A2: Never explored alternatives
  detected_A2 = False
  score_A2 = 0.0
  IF anchor_question_count >= 3 AND alternative_question_count == 0:
    detected_A2 = True
    score_A2 = 0.85

  # Combine rules — detected if either rule fires
  detected = detected_A1 OR detected_A2
  score = max(score_A1, score_A2)

  # Build reason string
  IF detected:
    reason = (
      f"{anchor_question_count} of your {total_questions} questions "
      f"focused on {case_config['anchor_topic']} symptoms. "
      f"You asked {alternative_question_count} questions exploring "
      f"alternative causes."
    )
  ELSE:
    reason = "No significant anchoring pattern detected."

  RETURN {
    "detected": detected,
    "score": score,
    "reason": reason,
    "evidence": anchor_evidence[:3]  # return max 3 examples
  }

---

### FUNCTION: detect_premature_closure(session, case_config)

PURPOSE: Checks if user concluded before conducting a thorough workup.

PSEUDOCODE:
FUNCTION detect_premature_closure(session, case_config):

  minimum_questions = case_config["minimum_questions"]
  required_topics = case_config["required_topics"]
  topics_covered = session["topics_covered"]
  question_count = session["question_count"]

  # RULE P1: Too few total questions asked
  detected_P1 = False
  score_P1 = 0.0
  IF question_count < minimum_questions:
    detected_P1 = True
    score_P1 = round(1.0 - (question_count / minimum_questions), 2)
    score_P1 = max(score_P1, 0.1)  # minimum score of 0.1 if detected

  # RULE P2: Too few required topics covered
  topics_hit = [t for t in required_topics IF t IN topics_covered]
  coverage_ratio = len(topics_hit) / len(required_topics)
  detected_P2 = False
  score_P2 = 0.0
  IF coverage_ratio < 0.60:
    detected_P2 = True
    score_P2 = round(1.0 - coverage_ratio, 2)

  # Combine — use worst score
  detected = detected_P1 OR detected_P2
  score = max(score_P1, score_P2)

  topics_missed = [t for t in required_topics IF t NOT IN topics_covered]

  # Build reason string
  IF detected_P1 AND detected_P2:
    reason = (
      f"You asked only {question_count} questions "
      f"(minimum recommended: {minimum_questions}) and covered "
      f"{len(topics_hit)} of {len(required_topics)} key history areas. "
      f"Areas not explored: {', '.join(topics_missed)}."
    )
  ELIF detected_P1:
    reason = (
      f"You submitted a diagnosis after only {question_count} questions. "
      f"A thorough workup typically requires at least {minimum_questions}."
    )
  ELIF detected_P2:
    reason = (
      f"You covered {len(topics_hit)} of {len(required_topics)} "
      f"key history areas before concluding. "
      f"Areas not explored: {', '.join(topics_missed)}."
    )
  ELSE:
    reason = "No premature closure detected — thorough workup completed."

  RETURN {
    "detected": detected,
    "score": score,
    "reason": reason,
    "evidence": topics_missed
  }

---

### FUNCTION: detect_confirmation_bias(session, case_config)

PURPOSE: Checks if user only sought confirming evidence for the
anchor diagnosis and never explored contradictory information.

PSEUDOCODE:
FUNCTION detect_confirmation_bias(session, case_config):

  contradictory_clues = case_config["contradictory_clues"]
  anchor_keywords = case_config["anchor_keywords"]
  all_questions = session["questions_asked"]
  diagnosis = session["diagnosis_submitted"]
  anchor_topic = case_config["anchor_topic"]

  # Count how many contradictory clue topics the user asked about
  # Each clue has key words — check if user asked about any of them
  clues_explored = 0
  FOR each clue IN contradictory_clues:
    clue_lower = lowercase(clue)
    clue_keywords = clue_lower.split()  # rough keyword extraction
    FOR each question IN all_questions:
      question_lower = lowercase(question)
      # Check if any significant word from this clue appears in question
      significant_words = [w for w in clue_keywords IF len(w) > 4]
      FOR each word IN significant_words:
        IF word IN question_lower:
          clues_explored = clues_explored + 1
          BREAK to next clue  # count each clue once

  # RULE C1: Diagnosed anchor but never explored contradictory clues
  detected_C1 = False
  score_C1 = 0.0
  diagnosis_matches_anchor = False

  IF diagnosis IS NOT None:
    diagnosis_lower = lowercase(diagnosis)
    FOR each keyword IN anchor_keywords:
      IF keyword IN diagnosis_lower:
        diagnosis_matches_anchor = True
        BREAK

  IF diagnosis_matches_anchor AND clues_explored == 0:
    detected_C1 = True
    score_C1 = 0.90

  # RULE C2: Very low contradictory clue exploration regardless of diagnosis
  detected_C2 = False
  score_C2 = 0.0
  exploration_ratio = clues_explored / len(contradictory_clues)
  IF exploration_ratio < 0.25 AND len(all_questions) >= 5:
    detected_C2 = True
    score_C2 = round(1.0 - exploration_ratio, 2)

  detected = detected_C1 OR detected_C2
  score = max(score_C1, score_C2)

  # Build reason string
  IF detected:
    reason = (
      f"You explored {clues_explored} of {len(contradictory_clues)} "
      f"key pieces of information that could have challenged your initial "
      f"assumption. Confirmation bias occurs when we only seek evidence "
      f"that supports our first instinct."
    )
  ELSE:
    reason = "No significant confirmation bias detected."

  RETURN {
    "detected": detected,
    "score": score,
    "reason": reason,
    "evidence": [f"Only {clues_explored}/{len(contradictory_clues)} contradictory areas explored"]
  }

---
---

## MODULE 3: feedback_generator.py

### Purpose
Takes bias detection results and generates Socratic feedback using
the Gemini API. Never reveals the correct diagnosis. Only asks
guiding questions that prompt the user to reconsider their reasoning.

IMPORTANT: Uses the NEW google-genai library (not deprecated google-generativeai)
Model: gemini-2.5-flash
Called by app.py after /conclude once bias_detector has run.

---

### FUNCTION: generate_feedback(bias_results, session, case_config)

PURPOSE: Main entry point. Builds prompt and calls Gemini to generate
Socratic feedback messages. Returns a list of feedback strings.

PSEUDOCODE:
FUNCTION generate_feedback(bias_results, session, case_config):

  # Step 1: Collect which biases were detected
  detected_biases = []
  FOR each bias_name, result IN bias_results:
    IF result["detected"] == True:
      detected_biases.append({
        "name": bias_name,
        "score": result["score"],
        "reason": result["reason"],
        "evidence": result["evidence"]
      })

  # Step 2: If no biases detected, return positive feedback
  IF len(detected_biases) == 0:
    RETURN [
      "Well done — your consultation showed thorough and balanced reasoning.",
      "You covered the key history areas and explored multiple possibilities.",
      "Consider what additional information might help confirm your diagnosis."
    ]

  # Step 3: Build the feedback prompt
  prompt = build_feedback_prompt(detected_biases, session, case_config)

  # Step 4: Call Gemini API using NEW google-genai library
  TRY:
    FROM google IMPORT genai
    FROM google.genai IMPORT types
    IMPORT os
    FROM dotenv IMPORT load_dotenv

    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    response = client.models.generate_content(
      model="gemini-2.5-flash",
      contents=prompt,
      config=types.GenerateContentConfig(
        system_instruction="""You are a medical education tutor
providing Socratic feedback to a student after a clinical consultation
exercise. Your role is to ask guiding questions that help the student
reflect on their reasoning process. You must NEVER reveal the correct
diagnosis. You must NEVER tell the student they were wrong directly.
You must ONLY ask questions that prompt deeper thinking.
Keep your response to 3-4 short Socratic questions maximum.
Each question should be on a new line.""",
        max_output_tokens=300,
        temperature=0.7
      )
    )

    feedback_text = response.text

  EXCEPT Exception as e:
    # If Gemini call fails, return rule-based fallback feedback
    feedback_text = build_fallback_feedback(detected_biases, case_config)

  # Step 5: Split into individual feedback messages by newline
  feedback_messages = [
    line.strip()
    for line in feedback_text.split("\n")
    if len(line.strip()) > 10
  ]

  RETURN feedback_messages[:4]  # max 4 feedback messages

---

### FUNCTION: build_feedback_prompt(detected_biases, session, case_config)

PURPOSE: Constructs the text prompt sent to Gemini for feedback.
Contains enough context for Gemini to generate relevant questions
without revealing the correct diagnosis.

PSEUDOCODE:
FUNCTION build_feedback_prompt(detected_biases, session, case_config):

  # Build bias description section
  bias_descriptions = ""
  FOR each bias IN detected_biases:
    bias_descriptions += f"\n- {bias['name']}: {bias['reason']}"

  prompt = f"""
A student has just completed a virtual patient consultation exercise.

CASE CONTEXT (do not reveal this to the student):
Patient: {case_config['patient_intro']}
Correct diagnosis: {case_config['correct_diagnosis']}
Anchor trap in this case: {case_config['anchor_topic']}

STUDENT BEHAVIOR:
- Total questions asked: {session['question_count']}
- Topics covered: {', '.join(session['topics_covered'])}
- Diagnosis submitted: {session['diagnosis_submitted']}

BIASES DETECTED:
{bias_descriptions}

TASK:
Generate 3-4 Socratic questions to help this student reflect on
their reasoning. Do not reveal the correct diagnosis. Do not say
the student was wrong. Do not use the word "bias". Ask questions
that naturally lead the student to reconsider what they may have
missed. Make each question specific to this case and this student's
actual behavior during the consultation.
"""

  RETURN prompt

---

### FUNCTION: build_fallback_feedback(detected_biases, case_config)

PURPOSE: Returns simple rule-based feedback if Gemini API call fails.
This ensures the system still gives useful output even without internet.

PSEUDOCODE:
FUNCTION build_fallback_feedback(detected_biases, case_config):
  messages = []

  FOR each bias IN detected_biases:

    IF bias["name"] == "anchoring":
      messages.append(
        f"You focused significantly on {case_config['anchor_topic']} "
        f"causes. What other body systems could produce these symptoms?"
      )
      messages.append(
        "Did you ask about all the patient's regular medications? "
        "Sometimes the cause is not the most obvious one."
      )

    IF bias["name"] == "premature_closure":
      messages.append(
        "You submitted your diagnosis relatively early. "
        "What additional history might change your thinking?"
      )
      IF len(bias["evidence"]) > 0:
        missed = bias["evidence"][0]
        messages.append(
          f"You did not ask about {missed.replace('_', ' ')}. "
          f"How might that information affect your assessment?"
        )

    IF bias["name"] == "confirmation_bias":
      messages.append(
        "Were there questions you chose not to ask because you already "
        "felt confident in your diagnosis?"
      )
      messages.append(
        "What information, if present, would make you reconsider "
        "your current diagnosis entirely?"
      )

  RETURN "\n".join(messages[:4])

---
---

## MODULE 4: app.py (Gemini integration section only)

### Purpose
This pseudocode covers only the Gemini call in the /chat route.
The full app.py skeleton is written on Day 4.

IMPORTANT: Using NEW google-genai library throughout.

---

### Gemini virtual patient call in POST /chat route

PSEUDOCODE:
ON POST /chat request:

  user_message = request.json["message"]
  case_id = session["case_id"]
  case = get_case(case_id)
  conversation_history = session["conversation"]

  # Build Gemini conversation history in correct format
  # NEW library uses "user" and "model" roles (not "assistant")
  gemini_contents = []
  FOR each message IN conversation_history:
    IF message["role"] == "user":
      role = "user"
    ELSE:
      role = "model"  # NOTE: "model" not "assistant" — this is new library format
    gemini_contents.append(
      types.Content(
        role=role,
        parts=[types.Part(text=message["content"])]
      )
    )

  # Add the new user message
  gemini_contents.append(
    types.Content(
      role="user",
      parts=[types.Part(text=user_message)]
    )
  )

  # Call Gemini with patient system prompt
  response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=gemini_contents,
    config=types.GenerateContentConfig(
      system_instruction=case["system_prompt"],
      max_output_tokens=200,
      temperature=0.7
    )
  )

  patient_reply = response.text

  # Update session tracking
  update_session(session_data, user_message)
  conversation_history.append({"role": "user", "content": user_message})
  conversation_history.append({"role": "model", "content": patient_reply})
  session["conversation"] = conversation_history

  RETURN jsonify({
    "response": patient_reply,
    "question_count": session_data["question_count"]
  })

---
---

## SESSION JSON LOG FORMAT
## Every completed session is saved as a JSON file in sessions/
## This becomes your research data for the evaluation phase.

{
  "session_id": "case1_20260520_143022",
  "case_id": "case_1",
  "case_title": "The Chest Pain Trap",
  "correct_diagnosis": "GERD",
  "start_time": "2026-05-20T14:30:22",
  "end_time": "2026-05-20T14:45:11",
  "time_taken_seconds": 889,
  "question_count": 9,
  "questions_asked": [
    "Does the pain go to your arm?",
    "Do you have shortness of breath?",
    "Any family history of heart disease?",
    "How bad is the pain out of 10?",
    "Are you on any medications?",
    "Does eating affect the pain?",
    "What does the pain feel like?",
    "Does it get worse when lying down?",
    "Any nausea or sweating?"
  ],
  "topics_covered": [
    "radiation", "associated_symptoms", "family_history",
    "medications", "meal_relationship", "pain_character",
    "relieving_factors"
  ],
  "diagnosis_submitted": "cardiac angina",
  "biases_detected": {
    "anchoring": {
      "detected": true,
      "score": 0.44,
      "reason": "4 of 9 questions focused on cardiac symptoms..."
    },
    "premature_closure": {
      "detected": false,
      "score": 0.11,
      "reason": "Covered 7 of 8 required topics..."
    },
    "confirmation_bias": {
      "detected": true,
      "score": 0.72,
      "reason": "Only explored 2 of 8 contradictory clues..."
    }
  },
  "feedback_given": [
    "You asked about radiation and shortness of breath early on...",
    "What other body systems might cause burning chest pain?",
    "Did you ask about the patient's regular medications?",
    "How might eating habits be relevant to chest pain?"
  ]
}

