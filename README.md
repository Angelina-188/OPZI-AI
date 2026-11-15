# OPZI AI – AI-Powered Career Assistant

OPZI AI is an AI-powered career eligibility analysis tool that helps job seekers understand how well their CV matches a specific job opportunity.

Users can upload their CV and enter a job description to receive an eligibility score, identify matching and missing skills, and get an overall recommendation.

✨Features

- **Eligibility Score:** Provides an estimated score based on the CV and job requirements.
- **Eligibility Summary:** Gives an overview of the candidate's suitability.
- **Skills Match:** Identifies skills and keywords found in both the CV and job description.
- **Skills Missing:** Highlights relevant skills and requirements not identified in the CV.
- **AI-Powered Analysis:** Generates an explanation of the candidate's strengths and areas to improve.
- **Overall Recommendation:** Provides a final assessment of the candidate's suitability.

✨ Technologies Used

- Python
- Flask
- HTML
- CSS
- JavaScript
- LM Studio
- Qwen 2.5 VL 7B (local AI model)
- PDF and DOCX text extraction

✨ Project Structure

```text
OPZI AI/
│
├── app.py
├── requirements.txt
├── .env
├── .gitignore
│
├── templates/
│   └── index.html
│
└── static/
    ├── style.css
    └── script.js
```

✨ Installation and Setup

### 1. Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
```

Replace the placeholder with your repository URL.

### 2. Open the Project Folder

```bash
cd OPZI-AI
```

### 3. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Set Up LM Studio

1. Download and install LM Studio.
2. Download the Qwen 2.5 VL 7B model.
3. Load the model in LM Studio.
4. Start the local server.
5. Make sure the API endpoint is:

```text
http://127.0.0.1:1234/v1/chat/completions
```

### 6. Run the Application

```bash
python app.py
```

Open the following address in your browser:

```text
http://127.0.0.1:5000
```

✨ How to Use OPZI AI

1. Open the OPZI AI application.
2. Upload your CV in PDF or DOCX format.
3. Paste the job description into the provided text area.
4. Click the Analyse button.
5. Review your eligibility score and analysis.
6. Check your matching and missing skills.
7. Read the overall recommendation.

✨ Important Notes

- The application uses a locally hosted AI model through LM Studio.
- LM Studio must be running with the selected model loaded before analysis.
- The eligibility score is an estimate and does not guarantee selection for a job.
- Analysis accuracy depends on the information provided in the CV and job description.

✨ Future Improvements

- Improve skill-matching accuracy.
- Enhance AI analysis and recommendations.
- Add additional CV formats.
- Improve the user interface and user experience.

---

**OPZI AI – Understand Your Job Eligibility.**
