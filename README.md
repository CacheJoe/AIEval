# AIALES

Academic Integrity & Automated Lab Evaluation System (AIALES) is now streamlined for a fast two-role workflow:

- `ADMIN` creates faculty users and subject records
- `FACULTY` creates experiments, adds context/reference content, uploads PDFs, and gets results

Detailed operating steps are in [USER_GUIDE.md](/C:/Users/RCOEM/Documents/lab%20assessment/USER_GUIDE.md).

## Current Product Shape

- FastAPI backend with modular services
- Streamlit frontend with a reduced `Home`, `Workspace`, and `Users` flow
- SQLite local development with PostgreSQL-ready configuration
- Subject -> Experiment -> Upload -> Evaluate workflow
- PDF structure analysis, plagiarism checks, relevance scoring, and marks
- PDF structure analysis, classmate plagiarism checks, heuristic AI-content risk, relevance scoring, and a final score out of 5
- File-driven submitter labels from filenames or manifest JSON
- Faster defaults:
  - TF-IDF relevance engine by default
  - screenshot forensics disabled by default
  - report generation removed from the evaluation request path

## Quick Start

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Copy the environment file:

   ```bash
   copy config\\.env.example config\\.env
   ```

3. Start the API:

   ```bash
   uvicorn app.main:app --reload
   ```

4. Seed local sample data:

   ```bash
   python scripts/seed_sample_data.py
   ```

5. Start Streamlit:

   ```bash
   streamlit run frontend/streamlit_app.py
   ```

## Default Accounts

- `admin@aiales.local` / `ChangeMe123!`
- `faculty@aiales.local` / `Faculty123!`

## Main Flow

1. Admin creates faculty users
2. Admin creates subject records and assigns faculty
3. Faculty creates experiments
4. Faculty adds experiment context and expected content
5. Faculty uploads PDFs
6. Faculty runs evaluation
7. Faculty reviews results and downloads CSV

## Runtime Notes

- `FRONTEND_LONG_READ_TIMEOUT_SECONDS` controls how long Streamlit waits for long uploads and evaluation calls
- `RELEVANCE_ENGINE=tfidf` is the current fast default
- `ENABLE_SCREENSHOT_FORENSICS=false` is the current fast default

## Project Layout

```text
app/
frontend/
database/migrations/
config/
logs/
reports/
submissions/
scripts/
```
