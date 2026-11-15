import io
import json
import re
import unicodedata
import os

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from pypdf import PdfReader
from docx import Document

load_dotenv()

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

# AI CONFIGURATION

LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"

MODEL_NAME = "qwen/qwen2.5-vl-7b:2"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

AI_PROVIDER = os.getenv("AI_PROVIDER", "local").lower()


# CONNECT TO LM STUDIO OR GEMINI

def ask_ai(prompt):

    # OPTION 1: LOCAL LM STUDIO

    if AI_PROVIDER == "local":

        data = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 1800,
            "stream": False
        }

        response = requests.post(
            LM_STUDIO_URL,
            json=data,
            timeout=300
        )

        response.raise_for_status()

        result = response.json()

        return result["choices"][0]["message"]["content"]


    # OPTION 2: ONLINE GEMINI

    elif AI_PROVIDER == "gemini":

        if not GEMINI_API_KEY:
            raise ValueError("Gemini API key is missing.")

        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{GEMINI_MODEL}:generateContent"
        )

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        }

        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1800
            }
        }

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=180
        )

        response.raise_for_status()

        result = response.json()

        try:
            return result["candidates"][0]["content"]["parts"][0]["text"]

        except (KeyError, IndexError, TypeError):
            raise ValueError("Gemini returned an empty or invalid response.")


    else:

        raise ValueError("Invalid AI provider configuration.")

    
# 2. EXTRACT VALID JSON FROM AI RESPONSE

def extract_json(ai_response):

    cleaned = ai_response.strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("AI did not return valid JSON.")

    return json.loads(cleaned[start:end + 1])


# 3. NORMALISE TEXT

def normalise(text):

    text = unicodedata.normalize("NFKC", str(text or ""))

    text = text.lower()

    text = text.replace("&", " and ")

    text = re.sub(r"[^a-z0-9+#.]+", " ", text)

    return re.sub(r"\s+", " ", text).strip()


# 4. VERIFY EVIDENCE

def evidence_exists(evidence, source_text):

    evidence = normalise(evidence)
    source = normalise(source_text)

    if not evidence:
        return False

    return evidence in source


# 5. EXTRACT JOB REQUIREMENTS

def extract_job_requirements(job_description):

    prompt = f"""
You are an information extraction assistant.

Read the job description and extract its actual requirements.

Return ONLY valid JSON in this format:

{{
    "job_title": "Job title",
    "company": "Company name if available",
    "requirements": [
        {{
            "name": "Short requirement name",
            "category": "education, technical_skill, soft_skill, experience, responsibility, location, availability or other",
            "priority": "mandatory or preferred",
            "evidence": "An exact quotation copied from the job description",
            "verifiable_in_cv": true
        }}
    ]
}}

RULES:

1. Extract only requirements explicitly stated in the job description.
2. Do not invent requirements.
3. Separate mandatory requirements from preferred requirements.
4. Do not treat responsibilities as candidate skills unless they are explicitly required.
5. Keep each requirement separate.
6. Do not add irrelevant skills.
7. Evidence must be copied exactly from the job description.
8. Use verifiable_in_cv=false for requirements that normally cannot be established from a CV, such as future availability.
9. Do not assume that a candidate meets any requirement.
10. Return JSON only.

JOB DESCRIPTION:

{job_description[:12000]}
"""

    result = extract_json(ask_ai(prompt))

    if not isinstance(result.get("requirements"), list):
        raise ValueError("Job requirements could not be extracted.")

    verified_requirements = []

    for item in result["requirements"]:

        if not isinstance(item, dict):
            continue

        name = str(item.get("name", "")).strip()
        evidence = str(item.get("evidence", "")).strip()

        if not name:
            continue

        if not evidence_exists(evidence, job_description):
            continue

        priority = str(item.get("priority", "mandatory")).lower()

        if priority not in ["mandatory", "preferred"]:
            priority = "mandatory"

        category = str(item.get("category", "other")).lower()

        verified_requirements.append({
            "name": name,
            "category": category,
            "priority": priority,
            "evidence": evidence,
            "verifiable_in_cv": bool(
                item.get("verifiable_in_cv", True)
            )
        })

    if not verified_requirements:
        raise ValueError("No verifiable job requirements were extracted.")

    return {
        "job_title": result.get("job_title", "Job Opportunity"),
        "company": result.get("company", ""),
        "requirements": verified_requirements
    }


# 6. EXTRACT CV INFORMATION

def extract_cv_information(cv_text):

    prompt = f"""
You are a CV information extraction assistant.

Extract information that is explicitly stated in the CV.

Return ONLY valid JSON in this format:

{{
    "education": [],
    "skills": [],
    "experience": [],
    "volunteering": [],
    "certifications": [],
    "languages": [],
    "other_information": []
}}

Every item must use this structure:

{{
    "value": "Extracted information",
    "evidence": "Exact quotation copied from the CV"
}}

RULES:

1. Never invent qualifications or experience.
2. Preserve the candidate's actual wording where possible.
3. Separate employment from volunteering.
4. Do not infer communication skills just because someone worked in sales.
5. Do not infer availability unless explicitly stated.
6. Do not assume a degree subject.
7. Every evidence quotation must appear in the CV.
8. Return JSON only.

CV:

{cv_text[:12000]}
"""

    result = extract_json(ask_ai(prompt))

    sections = [
        "education",
        "skills",
        "experience",
        "volunteering",
        "certifications",
        "languages",
        "other_information"
    ]

    verified = {}

    for section in sections:

        verified[section] = []

        for item in result.get(section, []):

            if not isinstance(item, dict):
                continue

            value = str(item.get("value", "")).strip()
            evidence = str(item.get("evidence", "")).strip()

            if value and evidence_exists(evidence, cv_text):

                verified[section].append({
                    "value": value,
                    "evidence": evidence
                })

    return verified


# 7. RELATED SKILL MAPPING

RELATED_SKILLS = {
    "communication": [
        "telesales",
        "customer service",
        "customer support",
        "client interaction"
    ],

    "interpersonal skills": [
        "telesales",
        "customer service",
        "customer support",
        "client interaction"
    ],

    "event management": [
        "event volunteering",
        "event volunteer",
        "event support",
        "event organisation",
        "event organization"
    ],

    "event experience": [
        "event volunteering",
        "event volunteer",
        "event support"
    ],

    "customer interaction": [
        "telesales",
        "customer service",
        "customer support"
    ],

    "business networking": [
        "business development",
        "professional networking",
        "client relationship management"
    ]
}


# 8. CHECK EXACT MATCHES


def check_exact_match(requirement, cv_text):

    name = normalise(requirement)

    cv = normalise(cv_text)

    aliases = {
        "microsoft excel": [
            "ms excel",
            "excel"
        ],
        "power bi": [
            "powerbi"
        ],
        "microsoft word": [
            "ms word"
        ],
        "masters degree": [
            "master's degree",
            "master degree",
            "postgraduate degree"
        ],
        "postgraduate student": [
            "masters student",
            "master's student",
            "postgraduate"
        ],
        "event volunteering": [
            "event volunteer",
            "volunteering for events",
            "volunteer at events"
        ]
    }

    possible_terms = [name]

    possible_terms.extend(aliases.get(name, []))

    for term in possible_terms:

        if normalise(term) in cv:

            return {
                "matched": True,
                "evidence": term
            }

    return {
        "matched": False,
        "evidence": ""
    }


# 9. CHECK RELATED MATCHES

def check_related_match(requirement, cv_text):

    requirement_name = normalise(requirement)

    cv = normalise(cv_text)

    related_terms = RELATED_SKILLS.get(
        requirement_name,
        []
    )

    for term in related_terms:

        if normalise(term) in cv:

            return {
                "matched": True,
                "evidence": term
            }

    return {
        "matched": False,
        "evidence": ""
    }


# 10. MATCH REQUIREMENTS AGAINST CV

def match_requirements(requirements, cv_text):

    exact_matches = []
    related_matches = []
    missing_requirements = []
    unconfirmed_requirements = []

    score_points = 0
    total_points = 0

    for requirement in requirements:

        name = requirement["name"]

        priority = requirement["priority"]

        weight = 3 if priority == "mandatory" else 1

        if not requirement["verifiable_in_cv"]:

            unconfirmed_requirements.append({
                **requirement,
                "status": "unconfirmed",
                "reason": "This requirement cannot be confirmed from the CV alone."
            })

            continue

        total_points += weight

        exact = check_exact_match(name, cv_text)

        if exact["matched"]:

            exact_matches.append({
                **requirement,
                "status": "exact",
                "cv_evidence": exact["evidence"]
            })

            score_points += weight

            continue

        related = check_related_match(name, cv_text)

        if related["matched"]:

            related_matches.append({
                **requirement,
                "status": "related",
                "cv_evidence": related["evidence"]
            })

            score_points += weight * 0.6

            continue

        missing_requirements.append({
            **requirement,
            "status": "missing",
            "reason": "No supporting evidence was found in the CV."
        })

    score = None

    if total_points > 0:

        score = round(
            (score_points / total_points) * 100
        )

    return {
        "score": score,
        "exact_matches": exact_matches,
        "related_matches": related_matches,
        "missing_requirements": missing_requirements,
        "unconfirmed_requirements": unconfirmed_requirements,
        "assessed_requirements": len(requirements) - len(unconfirmed_requirements),
        "total_requirements": len(requirements)
    }


# 11. GENERATE AI EXPLANATION


def generate_explanation(
    job_title,
    cv_information,
    match_results
):

    prompt = f"""
You are OPZI AI, a career eligibility assistant.

Create a short, honest candidate assessment.

JOB TITLE:
{job_title}

VERIFIED CV INFORMATION:
{json.dumps(cv_information, ensure_ascii=False)}

VERIFIED MATCH RESULTS:
{json.dumps(match_results, ensure_ascii=False)}

Provide these sections:

1. ELIGIBILITY SUMMARY
Explain the candidate's suitability.

2. STRENGTHS
Explain the strongest relevant qualifications and experience.

3. AREAS TO IMPROVE
Explain the important gaps.

4. OVERALL RECOMMENDATION
Give a clear final recommendation on whether the candidate should consider applying.
Base it on verified matches and missing requirements.
Be realistic and do not guarantee an interview or job offer.

FORMATTING RULES:

1. Use plain text headings only.
2. Do not use hashtags (#) before headings.
3. Do not use asterisks (*) around headings or titles.
4. Do not use decorative stars or emojis before headings.
5. Do not use Markdown formatting.
6. Keep headings short, clear and professional.
7. Separate each section with a blank line.

RULES:

- Use only the supplied verified information.
- Never invent experience or qualifications.
- Do not claim an unconfirmed skill is present.
- Do not treat unrelated skills as matches.
- Do not change the calculated eligibility score.
- Do not provide a separate list of application suggestions.
- Be supportive but realistic.
- Return plain text with clear headings.
"""

    return ask_ai(prompt)


# 12. HOMEPAGE

@app.route("/")
def home():

    return render_template("index.html")


# 13. HEALTH CHECK

@app.route("/health")
def health():

    return jsonify({
        "status": "running",
        "application": "OPZI AI"
    })


# 14. ANALYSE CV AND JOB DESCRIPTION

@app.route("/analyse", methods=["POST"])
def analyse():

    if "cv" not in request.files:

        return jsonify({
            "error": "Please upload your CV."
        }), 400

    cv = request.files["cv"]

    job_description = request.form.get(
        "jobDescription", ""
    ).strip()

    if not cv.filename:

        return jsonify({
            "error": "Please select a CV."
        }), 400

    if not job_description:

        return jsonify({
            "error": "Please enter a job description."
        }), 400

    try:

        file_content = cv.read()

        filename = cv.filename.lower()

        if filename.endswith(".pdf"):

            reader = PdfReader(
                io.BytesIO(file_content)
            )

            cv_text = "\n".join(
                page.extract_text() or ""
                for page in reader.pages
            )

        elif filename.endswith(".docx"):

            document = Document(
                io.BytesIO(file_content)
            )

            cv_text = "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
            )

        else:

            return jsonify({
                "error": "Only PDF and DOCX files are supported."
            }), 400

        if not cv_text.strip():

            return jsonify({
                "error": "No readable text found in your CV. Scanned PDFs may require OCR."
            }), 400

        # Extract job requirements.
        job_data = extract_job_requirements(
            job_description
        )

        # Extract CV information for the AI report.
        cv_information = extract_cv_information(
            cv_text
        )

        # Verify matches using Python.
        match_results = match_requirements(
            job_data["requirements"],
            cv_text
        )

        # Generate explanatory report.
        explanation = generate_explanation(
            job_data["job_title"],
            cv_information,
            match_results
        )

        # Combine exact and related matches.
        matched_keywords = (
            match_results["exact_matches"]
            + match_results["related_matches"]
        )

        # Combine missing and unconfirmed requirements.
        missing_keywords = (
            match_results["missing_requirements"]
            + match_results["unconfirmed_requirements"]
        )

        return jsonify({

            "status": "success",

            "message": "OPZI AI analysis completed!",

            "job_title": job_data["job_title"],

            "company": job_data["company"],

            "score": match_results["score"],

            "matched_keywords": matched_keywords,

            "missing_keywords": missing_keywords,

            "analysis": explanation

        })

    except requests.exceptions.Timeout:

        return jsonify({
            "error": "The AI model took too long to respond. Try a shorter CV or job description."
        }), 504

    except requests.exceptions.RequestException:

        return jsonify({
            "error": "Could not connect to LM Studio. Check that the server is running and the model is loaded."
        }), 503

    except (ValueError, json.JSONDecodeError) as error:

        print("Extraction error:", error)

        return jsonify({
            "error": "The AI returned an invalid response. Please try again."
        }), 422

    except Exception as error:

        print("Analysis error:", error)

        return jsonify({
            "error": "We could not analyse your CV. Please try again."
        }), 500


# 15. FILE SIZE ERROR

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "error": "Your CV must be smaller than 5 MB."
    }), 413


# 16. RUN APPLICATION

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
