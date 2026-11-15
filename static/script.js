const form = document.getElementById("eligibilityForm");

const cvInput = document.getElementById("cv");
const uploadArea = document.getElementById("uploadArea");
const fileName = document.getElementById("fileName");

const analyseButton = document.getElementById("analyseButton");
const message = document.getElementById("message");

const results = document.getElementById("results");

const MAX_FILE_SIZE = 5 * 1024 * 1024;


// FILE VALIDATION

function validateFile(file) {

    if (!file) {
        return "Please select your CV.";
    }

    const extension = file.name.split(".").pop().toLowerCase();

    if (!["pdf", "docx"].includes(extension)) {
        return "Only PDF and DOCX files are supported.";
    }

    if (file.size > MAX_FILE_SIZE) {
        return "Your CV must be smaller than 5 MB.";
    }

    return null;
}


// FILE SELECTION

cvInput.addEventListener("change", function () {

    const file = cvInput.files[0];

    const error = validateFile(file);

    if (error) {

        fileName.textContent = error;
        fileName.classList.add("error-text");

        cvInput.value = "";

        return;
    }

    fileName.textContent = "✓ " + file.name;
    fileName.classList.remove("error-text");

});


// DRAG AND DROP

uploadArea.addEventListener("click", function () {

    cvInput.click();

});


uploadArea.addEventListener("dragover", function (event) {

    event.preventDefault();

    uploadArea.classList.add("drag-active");

});


uploadArea.addEventListener("dragleave", function () {

    uploadArea.classList.remove("drag-active");

});


uploadArea.addEventListener("drop", function (event) {

    event.preventDefault();

    uploadArea.classList.remove("drag-active");

    const file = event.dataTransfer.files[0];

    if (!file) return;

    const error = validateFile(file);

    if (error) {

        fileName.textContent = error;
        fileName.classList.add("error-text");

        return;
    }

    const dataTransfer = new DataTransfer();

    dataTransfer.items.add(file);

    cvInput.files = dataTransfer.files;

    fileName.textContent = "✓ " + file.name;
    fileName.classList.remove("error-text");

});


// DISPLAY SKILLS MATCH AND SKILLS MISSING

function displayRequirements(containerId, requirements) {

    const container = document.getElementById(containerId);

    container.innerHTML = "";

    if (!requirements || requirements.length === 0) {

        container.innerHTML =
            '<p class="empty-result">No keywords to display.</p>';

        return;
    }

    requirements.forEach(function (item) {

        const tag = document.createElement("div");

        tag.className = "keyword-item";

        const name = document.createElement("strong");

        name.textContent = item.name;

        tag.appendChild(name);

        container.appendChild(tag);

    });

}


// DISPLAY AI ANALYSIS

function displayAnalysis(text) {

    const container = document.getElementById("analysisResult");

    container.innerHTML = "";

    const lines = (text || "").split("\n");

    const headings = [
        "ELIGIBILITY SUMMARY",
        "STRENGTHS",
        "AREAS TO IMPROVE",
        "OVERALL RECOMMENDATION"
    ];

    lines.forEach(function (line) {

        let cleanLine = line.trim();

        if (!cleanLine) return;

        // Remove Markdown heading symbols
        cleanLine = cleanLine.replace(/^#{1,6}\s*/, "");

        // Remove decorative stars and bullet symbols at the beginning
        cleanLine = cleanLine.replace(/^[*•⭐🌟✨★☆]+\s*/, "");

        // Remove Markdown bold and italic formatting
        cleanLine = cleanLine.replace(/\*\*/g, "");
        cleanLine = cleanLine.replace(/__/g, "");

        // Remove stars surrounding a title
        cleanLine = cleanLine.replace(/^\*+|\*+$/g, "");

        cleanLine = cleanLine.trim();

        if (!cleanLine) return;

        // Remove numbering temporarily when checking section titles
        const headingText = cleanLine
            .replace(/^\d+[.)]\s*/, "")
            .replace(/:$/, "")
            .trim();

        const isHeading = headings.includes(
            headingText.toUpperCase()
        );

        if (isHeading) {

            const heading = document.createElement("h4");

            heading.textContent = headingText;

            container.appendChild(heading);

        } else {

            const paragraph = document.createElement("p");

            paragraph.textContent = cleanLine;

            container.appendChild(paragraph);

        }

    });

}


// DISPLAY SCORE

function displayScore(score) {

    const scoreValue = document.getElementById("scoreValue");

    const scoreMessage = document.getElementById("scoreMessage");

    const scoreCircle = document.getElementById("scoreCircle");

    if (score === null || score === undefined) {

        scoreValue.textContent = "N/A";

        scoreMessage.textContent =
            "Not enough verifiable requirements to calculate a score.";

        scoreCircle.style.background =
            "linear-gradient(135deg, #e7e4f5, #d9d5eb)";

        return;
    }

    scoreValue.textContent = score + "%";

    if (score >= 80) {

        scoreMessage.textContent = "Strong requirement match";

    } else if (score >= 60) {

        scoreMessage.textContent = "Moderate requirement match";

    } else if (score >= 40) {

        scoreMessage.textContent = "Some relevant requirements matched";

    } else {

        scoreMessage.textContent = "Several requirements need attention";

    }

    const angle = score * 3.6;

    scoreCircle.style.background =
        `conic-gradient(#8175F5 ${angle}deg, #e9e6f5 ${angle}deg)`;

}


// DISPLAY COMPLETE RESULTS

function displayResults(data) {

    document.getElementById("jobTitle").textContent =
        data.job_title || "Job Opportunity";

    displayScore(data.score);

    displayRequirements(
        "skillsMatch",
        data.matched_keywords
    );

    displayRequirements(
        "skillsMissing",
        data.missing_keywords
    );

    displayAnalysis(data.analysis);

    results.hidden = false;

    results.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

}


// FORM SUBMISSION

form.addEventListener("submit", async function (event) {

    event.preventDefault();

    const file = cvInput.files[0];

    const error = validateFile(file);

    if (error) {

        message.textContent = error;

        message.className = "message error-message";

        return;
    }

    const jobDescription =
        document.getElementById("jobDescription").value.trim();

    if (!jobDescription) {

        message.textContent = "Please enter a job description.";

        message.className = "message error-message";

        return;
    }

    const formData = new FormData(form);

    analyseButton.disabled = true;

    analyseButton.textContent = "Analysing your CV...";

    message.textContent =
        "OPZI AI is extracting requirements and comparing your CV. This may take a few minutes.";

    message.className = "message loading-message";

    results.hidden = true;

    try {

        const response = await fetch("/analyse", {

            method: "POST",

            body: formData

        });

        const responseText = await response.text();

        let data;

        try {
            data = JSON.parse(responseText);
        } catch (error) {
            console.error("Server response:", responseText);

            throw new Error(
                `Server returned an invalid response. HTTP status: ${response.status}. Check the browser console.`
            );
        }

        if (!response.ok) {

            throw new Error(
                data.error || "Something went wrong."
            );

        }

        displayResults(data);

        message.textContent = data.message;

        message.className = "message success-message";

    } catch (error) {

        message.textContent = error.message;

        message.className = "message error-message";

    } finally {

        analyseButton.disabled = false;

        analyseButton.textContent = "Analyse My Eligibility";

    }

});


// NEW ANALYSIS

document.getElementById("newAnalysisButton")
    .addEventListener("click", function () {

        form.reset();

        fileName.textContent = "";

        fileName.classList.remove("error-text");

        message.textContent = "";

        message.className = "message";

        results.hidden = true;

        document.getElementById("checker")
            .scrollIntoView({
                behavior: "smooth"
            });

    });
