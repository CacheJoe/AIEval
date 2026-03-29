# AIALES USER GUIDE

This guide reflects the simplified production flow:

- `ADMIN` adds faculty and subject details
- `FACULTY` adds experiment topic, context, and expected content
- `FACULTY` uploads PDFs
- `FACULTY` runs evaluation and reviews results

Only `ADMIN` and `FACULTY` are part of the active workflow.

## 1. Quick Setup

### Install dependencies

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Create environment file

```powershell
Copy-Item config\.env.example config\.env
```

### Start the backend

```powershell
uvicorn app.main:app --reload
```

### Seed sample data

```powershell
python scripts\seed_sample_data.py
```

### Start the frontend

```powershell
streamlit run frontend\streamlit_app.py
```

## 2. Default Accounts

- `admin@aiales.local` / `ChangeMe123!`
- `faculty@aiales.local` / `Faculty123!`

## 3. What Admin Does

Admin uses:

- `Users`
- `Workspace`

### Step 1: Create faculty users

Open `Users` and add faculty accounts.

### Step 2: Create a subject

Open `Workspace`.

Under `Create Subject`:

- enter subject name
- enter semester or term
- choose faculty owner

This creates the subject record the faculty will work inside.

## 4. What Faculty Does

Faculty uses:

- `Home`
- `Workspace`

### Step 1: Select the subject

Use the left sidebar to choose the assigned subject.

### Step 2: Create an experiment

In `Workspace`, open `Create Experiment` and fill:

- `Experiment Topic`
- `Short Description`
- `Experiment Context`
- `Reference Content / Expected Coverage`

These fields help the evaluator score relevance more accurately.

### Step 3: Upload PDFs

In `Upload PDFs`:

- upload one or more `.pdf` files
- or upload a `.zip` containing PDFs

Optional:

- add manifest JSON to control the label shown in results

Example:

```json
{
  "lab_001.pdf": "23BCE101",
  "lab_002.pdf": "Aarav Patel"
}
```

### Step 4: Run evaluation

Click `Run Evaluation`.

The system will:

- extract text
- detect sections
- compute plagiarism similarities between classmates in the selected experiment
- estimate heuristic AI-generated-content risk
- measure relevance against experiment topic and reference text
- calculate a final score out of 5
- save results

### Step 5: Review results

Results are shown directly in the same workspace.

Each row includes:

- submitter label
- filename
- score out of 5
- plagiarism score
- plagiarism level
- top classmate similarity
- classmate match count
- AI-generated score
- AI-generated level
- relevance score
- flags
- scoring breakdown

### Step 6: Download results

Use the `Download Results CSV` button in the workspace after evaluation completes.

## 5. Runtime Optimization in This Version

This simplified build is tuned for faster turnaround:

- semantic relevance defaults to TF-IDF instead of loading the sentence-transformer model
- screenshot forensics is disabled by default
- evaluation no longer generates report artifacts automatically
- the Streamlit client waits longer for long-running upload and evaluation requests

Relevant environment variables:

- `FRONTEND_LONG_READ_TIMEOUT_SECONDS`
- `RELEVANCE_ENGINE`
- `ENABLE_SCREENSHOT_FORENSICS`

Recommended fast defaults:

```env
FRONTEND_LONG_READ_TIMEOUT_SECONDS=900
RELEVANCE_ENGINE=tfidf
ENABLE_SCREENSHOT_FORENSICS=false
```

## 6. Notes About Filenames

The system derives a display label from:

- filename stem
- email-like text inside the filename
- manifest JSON if provided

Better filenames produce cleaner result tables.

## 7. Troubleshooting

### Evaluation says only a few files were checked

That means only those files were saved as submissions for the selected experiment.

Check:

- the upload response table
- the selected experiment
- whether any files failed during upload

### Streamlit shows a backend read timeout

This usually means evaluation is still running longer than the client wait window.

Check:

- `logs/app.log`
- current value of `FRONTEND_LONG_READ_TIMEOUT_SECONDS`

### Evaluation is slow on first run

Use:

```env
RELEVANCE_ENGINE=tfidf
ENABLE_SCREENSHOT_FORENSICS=false
```

These are already the recommended defaults in this simplified flow.

## 8. Daily Workflow

1. Admin logs in
2. Admin creates faculty if needed
3. Admin creates subject and assigns faculty
4. Faculty logs in
5. Faculty creates experiment with context and expected content
6. Faculty uploads PDFs
7. Faculty runs evaluation
8. Faculty reviews results

## 9. Command Reference

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item config\.env.example config\.env
python scripts\seed_sample_data.py
uvicorn app.main:app --reload
streamlit run frontend\streamlit_app.py
```
