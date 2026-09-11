# Nidan — Bias-Aware Virtual Patient Simulator

A web-based clinical reasoning training tool for medical students.  
You interview a virtual patient, order investigations, perform examinations, submit a diagnosis — then receive detailed Socratic feedback on your reasoning process, not just whether you were right or wrong.

> **B.Tech Summer Internship 2026 — DAU (Dhirubhai Ambani University)  
> Student: Roll No. 202301408(Vraj Patel) and 202301114(Yogesh Bagotia) · Mentor: Abhishek Gupta · Area: Machine Learning

--- 

## What It Does

Students interact with an AI-powered virtual patient via a chat interface. The system tracks every question asked, every examination performed, and every investigation ordered, then at the end:

- **Evaluates the diagnosis** — correct / on the right track / anchored on the wrong cause / off-target
- **Detects three cognitive biases** in the student's reasoning process (without labelling them as biases):
  - *Anchoring* — fixating on the first or most obvious diagnosis
  - *Premature closure* — concluding before a thorough workup
  - *Confirmation bias* — only seeking evidence that supports one hypothesis
- **Generates Socratic feedback** via Gemini 2.5 Flash that coaches *how* to reason, not just what the right answer was
- **Shows a full scorecard** of every examination and investigation — what was essential and done ✓, what was essential and missed ○, what was appropriate, what was low-value ⚠, and what was irrelevant

### The Universal Panel Design

All five cases share the **same list of 86 investigations and 27 examination systems**. Students cannot infer the diagnosis from which tests are available — they see CT Pulmonary Angiogram, Anti-GAD Antibodies, and OGTT regardless of which case they are on. Only when they order a test does the result reveal whether it is relevant.

---

## Clinical Cases

| # | Patient | Presentation | True Diagnosis | Diagnostic Trap |
|---|---------|-------------|----------------|-----------------|
| 1 | Ramesh Kumar, 48M | Chest pain × 3 days | GERD (NSAID-induced) | Cardiac / ACS |
| 2 | Kavya Menon, 29F | Breathlessness + pleuritic chest pain × 2 days | Pulmonary Embolism | Chest infection / URTI |
| 3 | Gopal Mehta, 74M | Acute confusion since yesterday | UTI → Delirium | Stroke / Dementia |
| 4 | Meera Patel, 35F | Fatigue + weight gain × 3 months | Primary Hypothyroidism | Depression / Burnout |
| 5 | Aisha Khan, 21F | Vomiting + severe abdo pain, deep rapid breathing | DKA in new-onset T1DM | Gastroenteritis |

Cases 2 and 5 are lab-required — the diagnosis **cannot** be made from history alone; students must order the right investigations.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 + Flask |
| AI (patient voice + feedback) | Google Gemini 2.5 Flash via `google-genai` library |
| Bias detection | Rule-based engine (no LLM) |
| Frontend | Vanilla HTML / CSS / JavaScript — no frameworks |
| Session storage | Server-side dict (no database needed) |

---

## Prerequisites

- **Python 3.11** (3.10+ likely works; 3.12+ untested)
- **A Gemini API key** — free at [aistudio.google.com](https://aistudio.google.com/app/apikey)
- **Git** (to clone the repo)

> The free Gemini API tier has rate limits. If you see a "patient is taking a moment" message, wait a few seconds and retry — the app handles this automatically.

---

## Installation

### macOS

**1. Install Python 3.11**

Check if you already have it:
```bash
python3 --version
```

If not, install via [Homebrew](https://brew.sh):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.11
```

Or download the installer from [python.org/downloads](https://www.python.org/downloads/).

**2. Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/bias-aware-vp-simulator.git
cd bias-aware-vp-simulator
```

**3. Create and activate a virtual environment**
```bash
python3.11 -m venv venv
source venv/bin/activate
```

Your terminal prompt will change to show `(venv)` — this means the environment is active.

**4. Install dependencies**
```bash
pip install -r requirements.txt
```

**5. Set up your API key**
```bash
cp .env.example .env
open -e .env          # opens in TextEdit
```

Edit the file so it reads:
```
GEMINI_API_KEY=your_actual_key_here
FLASK_SECRET_KEY=any_random_string_you_choose
```

Save and close.

**6. Run the app**
```bash
python app.py
```

Open your browser at **http://localhost:5000**

---

### Windows

**1. Install Python 3.11**

Download the installer from [python.org/downloads](https://www.python.org/downloads/release/python-3110/).

> ⚠️ During installation, tick **"Add Python to PATH"** before clicking Install.

Verify in Command Prompt:
```cmd
python --version
```

**2. Install Git** (if not already installed)

Download from [git-scm.com](https://git-scm.com/download/win) and run the installer with default options.

**3. Clone the repository**

Open **Command Prompt** or **PowerShell**:
```cmd
git clone https://github.com/YOUR_USERNAME/bias-aware-vp-simulator.git
cd bias-aware-vp-simulator
```

**4. Create and activate a virtual environment**
```cmd
python -m venv venv
venv\Scripts\activate
```

Your prompt will change to show `(venv)`.

> If you get a PowerShell execution policy error, run this first:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

**5. Install dependencies**
```cmd
pip install -r requirements.txt
```

**6. Set up your API key**

Copy the example file:
```cmd
copy .env.example .env
notepad .env
```

Edit the file so it reads:
```
GEMINI_API_KEY=your_actual_key_here
FLASK_SECRET_KEY=any_random_string_you_choose
```

Save and close Notepad.

**7. Run the app**
```cmd
python app.py
```

Open your browser at **http://localhost:5000**

---

## Getting a Gemini API Key

1. Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with a Google account
3. Click **Create API key**
4. Copy the key and paste it into your `.env` file as shown above

The free tier is sufficient for development and small-scale evaluation sessions.

---

## Project Structure

```
bias-aware-vp-simulator/
│
├── app.py                   Flask app — all URL routes
├── cases.py                 5 clinical case definitions
│                            + MASTER_INVESTIGATIONS (86 tests)
│                            + MASTER_EXAMINATIONS   (27 systems)
├── session_tracker.py       Tracks questions asked, topics covered
├── bias_detector.py         Rule-based cognitive bias detection
├── clinical_evaluator.py    Diagnosis grading + exam/investigation scoring
├── feedback_generator.py    Socratic feedback via Gemini API
│
├── templates/
│   ├── index.html           Case selection home page
│   ├── pre_case.html        Pre-consultation questionnaire (year, confidence)
│   ├── chat.html            Main consultation interface (3 tabs)
│   └── feedback.html        Post-consultation feedback & scorecard
│
├── static/
│   ├── style.css            All styling (no external CSS frameworks)
│   └── chat.js              Tab switching, chat, exam, investigation logic
│
├── sessions/                JSON logs of completed sessions (research data)
├── docs/                    Design documents, sprint plan, references
│
├── requirements.txt         Python dependencies (pinned versions)
├── .env.example             Template for environment variables
└── README.md                This file
```

---

## How the Consultation Works

```
1. Select a case → fill in a short pre-case questionnaire (year of study, confidence)

2. Interview the patient
   → Type free-text questions in the History tab
   → The AI patient responds, revealing information only when directly asked

3. Examine the patient (Examination tab)
   → 27 clinical systems available (same list on every case)
   → Relevant systems return case-specific findings; others return normal findings

4. Order investigations (Investigations tab)
   → 86 tests available across 15 specialty groups (same list on every case)
   → Relevant tests return case-specific results; others return normal results

5. Submit your diagnosis → feedback page loads automatically

6. Review your feedback
   → Tutor feedback (Socratic, Gemini-generated)
   → History coverage grid (topics hit / missed)
   → Examination scorecard (essential ✓/○ · relevant · not needed)
   → Investigation scorecard (key ✓/○ · appropriate · low-value ⚠ · not needed)
   → Reasoning analysis (three cognitive patterns, no jargon labels)
```

---

## Stopping and Restarting

**Stop the server:** press `Ctrl+C` in the terminal.

**Restart:**
```bash
# macOS
source venv/bin/activate
python app.py

# Windows
venv\Scripts\activate
python app.py
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'flask'` | Virtual environment is not activated — run `source venv/bin/activate` (Mac) or `venv\Scripts\activate` (Windows) |
| `GEMINI_API_KEY not set` or blank responses | Check that `.env` exists and contains your key. Make sure there are no spaces around the `=` sign |
| "Patient is taking a moment" message | Free-tier rate limit hit — the app retries automatically. Wait a few seconds |
| Port 5000 already in use | Change the port: edit the last line of `app.py` to `app.run(debug=True, port=5001)` then open `http://localhost:5001` |
| `python3.11` not found on Mac | Use `python3` instead, or install via Homebrew: `brew install python@3.11` |
| PowerShell activation error on Windows | Run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` then retry |
| Session data lost between restarts | This is expected — sessions are stored in memory. Completed sessions are saved as JSON files in `sessions/` |

---

## Research Context

This tool was built to study **cognitive bias in clinical reasoning** among medical students. Each case is designed around a diagnostic trap — an obvious but incorrect hypothesis that an anchoring or premature-closure-prone reasoner will fall into. The system detects bias patterns rule-based (no LLM) and generates feedback that avoids naming the biases explicitly, following Socratic pedagogy.

Session data (anonymised) is saved to `sessions/` as JSON for research analysis.

---

## License

For academic and research use — DA-IICT internship project 2026.
