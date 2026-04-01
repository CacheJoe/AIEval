"""Streamlit ERP-style frontend for AIALES."""
import subprocess
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

def start_backend():
    subprocess.Popen(
        [
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000"
        ]
    )

start_backend()

time.sleep(3)
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

API_BASE_URL = os.getenv("FRONTEND_API_BASE_URL", "http://127.0.0.1:8000/api/v1")
REQUEST_CONNECT_TIMEOUT_SECONDS = float(os.getenv("FRONTEND_CONNECT_TIMEOUT_SECONDS", "10"))
REQUEST_READ_TIMEOUT_SECONDS = float(os.getenv("FRONTEND_READ_TIMEOUT_SECONDS", "60"))
LONG_REQUEST_READ_TIMEOUT_SECONDS = float(os.getenv("FRONTEND_LONG_READ_TIMEOUT_SECONDS", "900"))
PAGES = ["Home", "Workspace", "Users"]

LONG_RUNNING_PATH_HINTS = (
    "/submissions/upload",
    "/evaluate",
    "/reports",
)


def apply_theme() -> None:
    """Apply dashboard styling."""
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top right, rgba(15,118,110,0.10), transparent 28%),
                linear-gradient(180deg, #f3f7fa 0%, #f8fbfd 100%);
        }
        .hero-card, .panel-card {
            background: white;
            border: 1px solid #d7e2ea;
            border-radius: 18px;
            box-shadow: 0 16px 34px rgba(15, 23, 42, 0.06);
        }
        .hero-card { padding: 2rem; }
        .panel-card { padding: 1rem 1.2rem; margin-bottom: 1rem; }
        .metric-card {
            padding: 1rem;
            background: linear-gradient(180deg, #ffffff 0%, #f9fcfd 100%);
            border: 1px solid #dbe5eb;
            border-radius: 16px;
        }
        .small-label {
            color: #4b5563;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state() -> None:
    """Initialize session state."""
    defaults = {
        "access_token": None,
        "refresh_token": None,
        "current_user": None,
        "selected_class_id": None,
        "selected_experiment_id": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def clear_session() -> None:
    """Reset auth state."""
    st.session_state["access_token"] = None
    st.session_state["refresh_token"] = None
    st.session_state["current_user"] = None
    st.session_state["selected_class_id"] = None
    st.session_state["selected_experiment_id"] = None


def _request_timeout(path: str) -> tuple[float, float]:
    """Return a connect/read timeout pair tuned for the request type."""
    read_timeout = REQUEST_READ_TIMEOUT_SECONDS
    if any(hint in path for hint in LONG_RUNNING_PATH_HINTS):
        read_timeout = LONG_REQUEST_READ_TIMEOUT_SECONDS
    return (REQUEST_CONNECT_TIMEOUT_SECONDS, read_timeout)


def _refresh_session() -> bool:
    """Refresh access token once."""
    refresh_token = st.session_state.get("refresh_token")
    if not refresh_token:
        return False

    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/refresh",
            json={"refresh_token": refresh_token},
            timeout=_request_timeout("/auth/refresh"),
        )
    except requests.RequestException:
        return False

    if not response.ok:
        return False

    payload = response.json()
    st.session_state["access_token"] = payload["access_token"]
    st.session_state["refresh_token"] = payload["refresh_token"]
    st.session_state["current_user"] = payload["user"]
    return True


def api_request(
    method: str,
    path: str,
    *,
    token_required: bool = True,
    retry_on_refresh: bool = True,
    **kwargs: Any,
) -> requests.Response | None:
    """Call the backend API with automatic token refresh."""
    headers = kwargs.pop("headers", {})
    if token_required and st.session_state.get("access_token"):
        headers["Authorization"] = f"Bearer {st.session_state['access_token']}"

    try:
        response = requests.request(
            method,
            f"{API_BASE_URL}{path}",
            headers=headers,
            timeout=_request_timeout(path),
            **kwargs,
        )
    except requests.RequestException as exc:
        if "Read timed out" in str(exc):
            st.error(
                "The backend is taking longer than expected. "
                "Large uploads, first-time model loading, evaluation, and report generation can take several minutes."
            )
        else:
            st.error(f"Backend request failed: {exc}")
        return None

    if response.status_code == 401 and token_required and retry_on_refresh and _refresh_session():
        return api_request(method, path, token_required=token_required, retry_on_refresh=False, **kwargs)

    return response


def api_json(method: str, path: str, *, token_required: bool = True, **kwargs: Any) -> Any | None:
    """Return JSON response or show an error."""
    response = api_request(method, path, token_required=token_required, **kwargs)
    if response is None:
        return None
    if response.ok:
        return response.json()

    try:
        message = response.json().get("message", response.text)
    except Exception:
        message = response.text
    st.error(message)
    return None


def login_view() -> None:
    """Render login screen."""
    st.title("AIALES")
    st.caption("Academic Integrity & Automated Lab Evaluation System")
    st.markdown('<div class="hero-card">', unsafe_allow_html=True)
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="admin@aiales.local")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign In", use_container_width=True)

    if submitted:
        response = api_request(
            "POST",
            "/auth/login",
            token_required=False,
            json={"email": email, "password": password},
        )
        if response is not None and response.ok:
            payload = response.json()
            st.session_state["access_token"] = payload["access_token"]
            st.session_state["refresh_token"] = payload["refresh_token"]
            st.session_state["current_user"] = payload["user"]
            st.rerun()
        elif response is not None:
            try:
                st.error(response.json().get("message", "Login failed."))
            except Exception:
                st.error("Login failed.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.info(
        "Seed accounts: admin@aiales.local / ChangeMe123!, faculty@aiales.local / Faculty123!"
    )


def fetch_classes() -> list[dict[str, Any]]:
    """Load classes visible to the current user."""
    payload = api_json("GET", "/classes")
    return payload or []


def fetch_experiments(class_id: str | None) -> list[dict[str, Any]]:
    """Load experiments for the selected class."""
    if not class_id:
        return []
    payload = api_json("GET", f"/classes/{class_id}/experiments")
    return payload or []


def render_sidebar(classes: list[dict[str, Any]]) -> tuple[str, str | None, str | None]:
    """Render sidebar navigation and selectors."""
    user = st.session_state["current_user"]
    with st.sidebar:
        st.title("AIALES")
        st.write(user["name"])
        st.caption(user["role"])
        page = st.radio("Navigation", PAGES)

        if classes:
            class_options = {f"{item['name']} [{item['semester']}]": item["id"] for item in classes}
            selected_class_label = st.selectbox(
                "Subject",
                list(class_options.keys()),
                index=0 if st.session_state["selected_class_id"] is None else list(class_options.values()).index(
                    st.session_state["selected_class_id"]
                )
                if st.session_state["selected_class_id"] in class_options.values()
                else 0,
            )
            st.session_state["selected_class_id"] = class_options[selected_class_label]
        else:
            st.session_state["selected_class_id"] = None
            st.caption("No subjects available")

        experiments = fetch_experiments(st.session_state["selected_class_id"])
        if experiments:
            experiment_options = {item["topic"]: item["id"] for item in experiments}
            selected_experiment_label = st.selectbox(
                "Experiment",
                list(experiment_options.keys()),
                index=0 if st.session_state["selected_experiment_id"] is None else list(experiment_options.values()).index(
                    st.session_state["selected_experiment_id"]
                )
                if st.session_state["selected_experiment_id"] in experiment_options.values()
                else 0,
            )
            st.session_state["selected_experiment_id"] = experiment_options[selected_experiment_label]
        else:
            st.session_state["selected_experiment_id"] = None
            st.caption("No experiments available")

        if st.button("Logout", use_container_width=True):
            refresh_token = st.session_state.get("refresh_token")
            if refresh_token:
                api_request("POST", "/auth/logout", json={"refresh_token": refresh_token})
            clear_session()
            st.rerun()

    return page, st.session_state["selected_class_id"], st.session_state["selected_experiment_id"]


def render_metric_cards(cards: list[tuple[str, str]]) -> None:
    """Render metric-style cards."""
    columns = st.columns(len(cards))
    for column, (label, value) in zip(columns, cards):
        with column:
            st.markdown(
                f'<div class="metric-card"><div class="small-label">{label}</div><h3>{value}</h3></div>',
                unsafe_allow_html=True,
            )


def render_home(classes: list[dict[str, Any]]) -> None:
    """Render home dashboard."""
    user = st.session_state["current_user"]
    st.title("Academic Integrity Operations Console")
    render_metric_cards(
        [
            ("Role", user["role"]),
            ("Visible Subjects", str(len(classes))),
            ("API", API_BASE_URL),
        ]
    )

    st.subheader("Admin and Faculty Workflow")
    st.caption("Admin creates faculty and subjects. Faculty creates experiments, uploads PDFs, and gets results.")

    st.subheader("Subject Portfolio")
    if classes:
        st.dataframe(pd.DataFrame(classes), use_container_width=True)
    else:
        st.info("No subjects are available for your account yet.")


def render_manage_panel(selected_class_id: str | None) -> None:
    """Render subject and experiment management."""
    user = st.session_state["current_user"]
    manage_tabs = st.tabs(["Create Subject", "Create Experiment"])

    with manage_tabs[0]:
        if user["role"] != "ADMIN":
            st.info("Only administrators can create subjects.")
        else:
            users = api_json("GET", "/users") or []
            faculty_choices = {
                f"{item['name']} ({item['email']})": item["id"]
                for item in users
                if item["role"] == "FACULTY"
            }
            with st.form("create_class_form"):
                name = st.text_input("Subject Name")
                semester = st.text_input("Semester / Term", value="Semester 6")
                faculty_label = st.selectbox("Faculty Owner", list(faculty_choices.keys())) if faculty_choices else None
                submitted = st.form_submit_button("Create Subject", use_container_width=True)
            if submitted and faculty_label:
                payload = {
                    "name": name,
                    "semester": semester,
                    "faculty_id": faculty_choices[faculty_label],
                }
                result = api_json("POST", "/classes", json=payload)
                if result:
                    st.success(f"Created subject {result['name']}.")

    with manage_tabs[1]:
        if user["role"] not in {"ADMIN", "FACULTY"}:
            st.info("Only administrators and faculty can create experiments.")
        elif not selected_class_id:
            st.info("Select a subject from the sidebar first.")
        else:
            with st.form("create_experiment_form"):
                topic = st.text_input("Experiment Topic")
                description = st.text_area("Short Description")
                context = st.text_area("Experiment Context", help="Describe what this experiment is about and what the submission should demonstrate.")
                reference_content = st.text_area(
                    "Reference Content / Expected Coverage",
                    help="Paste expected points, theory, algorithm outline, or evaluation notes to improve relevance scoring.",
                )
                submitted = st.form_submit_button("Create Experiment", use_container_width=True)
            if submitted:
                result = api_json(
                    "POST",
                    f"/classes/{selected_class_id}/experiments",
                    json={
                        "topic": topic,
                        "description": description or None,
                        "context": context or None,
                        "reference_content": reference_content or None,
                    },
                )
                if result:
                    st.success(f"Created experiment {result['topic']}.")


def render_upload_panel(selected_experiment_id: str | None) -> None:
    """Render upload tools."""
    user = st.session_state["current_user"]
    st.subheader("Upload PDFs")
    if user["role"] not in {"ADMIN", "FACULTY"}:
        st.info("Only administrators and faculty can upload submissions.")
        return
    if not selected_experiment_id:
        st.info("Select an experiment from the sidebar first.")
        return

    uploads = st.file_uploader(
        "Upload PDF files or ZIP batches",
        type=["pdf", "zip"],
        accept_multiple_files=True,
    )
    manifest_text = st.text_area(
        "Optional manifest JSON for submitter labels",
        placeholder='{"23BCE101_lab1.pdf": "23BCE101", "missionaries.pdf": "Aarav Patel"}',
        help="Use this when filenames are generic and you want cleaner names in results and reports.",
    )
    if st.button("Upload Batch", use_container_width=True) and uploads:
        files = [("files", (upload.name, upload.getvalue(), upload.type or "application/octet-stream")) for upload in uploads]
        data = {"manifest_json": manifest_text} if manifest_text.strip() else None
        with st.spinner("Uploading files and saving submissions..."):
            response = api_request("POST", f"/experiments/{selected_experiment_id}/submissions/upload", files=files, data=data)
        if response is not None and response.ok:
            payload = response.json()
            saved_count = payload["created_count"] + payload["updated_count"]
            if saved_count == 0:
                st.error("Upload finished, but no submissions were actually saved.")
            elif payload["failed_count"] > 0:
                st.warning(
                    f"Upload completed with partial success. Saved {saved_count} file(s), "
                    f"failed {payload['failed_count']} file(s)."
                )
            else:
                st.success(f"Upload completed. Saved {saved_count} submission(s).")
            st.dataframe(pd.DataFrame(payload["items"]), use_container_width=True)
        elif response is not None:
            try:
                error_payload = response.json()
                st.error(error_payload.get("message", "Upload failed."))
                details = error_payload.get("details")
                if isinstance(details, dict) and details.get("items"):
                    st.dataframe(pd.DataFrame(details["items"]), use_container_width=True)
            except Exception:
                st.error("Upload failed.")

    submissions = api_json("GET", f"/experiments/{selected_experiment_id}/submissions")
    if submissions:
        st.markdown("### Current Submissions")
        st.dataframe(pd.DataFrame(submissions), use_container_width=True)


def render_results_panel(selected_experiment_id: str | None) -> None:
    """Render evaluation actions and results."""
    user = st.session_state["current_user"]
    st.subheader("Evaluate and Review Results")
    if not selected_experiment_id:
        st.info("Select an experiment from the sidebar first.")
        return

    if user["role"] in {"ADMIN", "FACULTY"} and st.button("Run Evaluation", use_container_width=True):
        with st.spinner("Running evaluation. This should return faster in the simplified mode..."):
            payload = api_json("POST", f"/experiments/{selected_experiment_id}/evaluate")
        if payload:
            st.success(f"Evaluated {payload['evaluated_count']} submissions.")

    results = api_json("GET", f"/experiments/{selected_experiment_id}/results")
    if results:
        result_dataframe = _results_dataframe(results)
        st.dataframe(result_dataframe, use_container_width=True)
        st.download_button(
            "Download Results CSV",
            data=result_dataframe.to_csv(index=False).encode("utf-8"),
            file_name=f"experiment_{selected_experiment_id}_results.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.markdown("### Download Summary Report")
        with st.spinner("Preparing summary report artifacts..."):
            summary = api_json("GET", f"/experiments/{selected_experiment_id}/reports")
        if summary:
            artifacts = _artifact_map(summary)
            report_columns = st.columns(2)
            with report_columns[0]:
                _render_download_button("Download Summary Report PDF", artifacts.get("summary_pdf"))
            with report_columns[1]:
                _render_download_button("Download Detailed Marks CSV", artifacts.get("marks_csv"))


def render_workspace(selected_class_id: str | None, selected_experiment_id: str | None) -> None:
    """Render the main admin and faculty workspace."""
    st.title("Workspace")
    render_manage_panel(selected_class_id)
    st.divider()
    render_upload_panel(selected_experiment_id)
    st.divider()
    render_results_panel(selected_experiment_id)


def _results_dataframe(results: list[dict[str, Any]]) -> pd.DataFrame:
    """Build a faculty-facing results table."""
    dataframe = pd.DataFrame(results)
    preferred_columns = [
        "submitter_label",
        "filename",
        "score_out_of_5",
        "plagiarism_score",
        "plagiarism_level",
        "top_classmate_similarity",
        "classmate_match_count",
        "ai_generated_score",
        "ai_generated_level",
        "relevance_score",
        "created_at",
    ]
    available_columns = [column for column in preferred_columns if column in dataframe.columns]
    return dataframe[available_columns] if available_columns else dataframe


def _artifact_map(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {artifact["name"]: artifact for artifact in summary.get("artifacts", [])}


def _render_download_button(label: str, artifact: dict[str, Any] | None) -> None:
    if artifact is None:
        st.caption(f"{label} not available")
        return

    path = Path(artifact["absolute_path"])
    if not path.exists():
        st.caption(f"{label} file missing on disk")
        return

    mime = "application/octet-stream"
    if path.suffix == ".csv":
        mime = "text/csv"
    elif path.suffix == ".pdf":
        mime = "application/pdf"
    elif path.suffix == ".html":
        mime = "text/html"

    st.download_button(label, data=path.read_bytes(), file_name=path.name, mime=mime, use_container_width=True)


def render_reports(selected_experiment_id: str | None) -> None:
    """Render reports page."""
    user = st.session_state["current_user"]
    st.title("Reports")

    if not selected_experiment_id:
        st.info("Select an experiment from the sidebar first.")
        return

    with st.spinner("Loading report artifacts..."):
        summary = api_json("GET", f"/experiments/{selected_experiment_id}/reports")
        network = api_json("GET", f"/experiments/{selected_experiment_id}/reports/network/data")
    if not summary:
        return

    render_metric_cards(
        [
            ("Submissions", str(summary["submission_count"])),
            ("Average Marks", str(summary["average_marks"])),
            ("Copy Clusters", str(summary["cluster_count"])),
        ]
    )

    artifacts = _artifact_map(summary)
    download_cols = st.columns(4)
    with download_cols[0]:
        _render_download_button("Download CSV", artifacts.get("marks_csv"))
    with download_cols[1]:
        _render_download_button("Download PDF", artifacts.get("summary_pdf"))
    with download_cols[2]:
        _render_download_button("Download Dashboard", artifacts.get("dashboard_html"))
    with download_cols[3]:
        _render_download_button("Download Network", artifacts.get("plagiarism_network_html"))

    st.subheader("Top Sources")
    top_sources = summary.get("top_sources", [])
    if top_sources:
        st.dataframe(pd.DataFrame(top_sources), use_container_width=True)
    else:
        st.info("No plagiarism clusters crossed the configured threshold.")

    if network:
        st.subheader("Network Summary")
        st.dataframe(pd.DataFrame(network.get("edges", [])), use_container_width=True)

    dashboard_artifact = artifacts.get("dashboard_html")
    if dashboard_artifact:
        dashboard_path = Path(dashboard_artifact["absolute_path"])
        if dashboard_path.exists():
            st.subheader("Interactive Dashboard")
            components.html(dashboard_path.read_text(encoding="utf-8"), height=900, scrolling=True)

    network_artifact = artifacts.get("plagiarism_network_html")
    if network_artifact:
        network_path = Path(network_artifact["absolute_path"])
        if network_path.exists():
            st.subheader("Plagiarism Network Graph")
            components.html(network_path.read_text(encoding="utf-8"), height=850, scrolling=True)


def render_users() -> None:
    """Render users page."""
    user = st.session_state["current_user"]
    st.title("Users")
    if user["role"] != "ADMIN":
        st.info("Only administrators can manage users.")
        return

    users = api_json("GET", "/users") or []
    visible_users = [item for item in users if item["role"] in {"ADMIN", "FACULTY"}]
    st.dataframe(pd.DataFrame(visible_users), use_container_width=True)

    with st.form("create_user_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name")
            email = st.text_input("Email")
        with col2:
            role = st.selectbox("Role", ["ADMIN", "FACULTY"])
            password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Create User", use_container_width=True)
    if submitted:
        payload = {
            "name": name,
            "email": email,
            "role": role,
            "password": password,
            "is_active": True,
        }
        result = api_json("POST", "/users", json=payload)
        if result:
            st.success(f"Created user {result['email']}.")


def render_settings() -> None:
    """Render settings page."""
    user = st.session_state["current_user"]
    st.title("Settings")
    if user["role"] != "ADMIN":
        st.info("Only administrators can view runtime settings.")
        return

    payload = api_json("GET", "/settings")
    if payload:
        st.json(payload, expanded=True)


def render_audit_log() -> None:
    """Render audit log page."""
    user = st.session_state["current_user"]
    st.title("Audit Log")
    if user["role"] != "ADMIN":
        st.info("Only administrators can view audit logs.")
        return

    col1, col2 = st.columns(2)
    with col1:
        limit = st.slider("Rows", min_value=25, max_value=500, value=200, step=25)
    with col2:
        action_filter = st.text_input("Action Filter", placeholder="EVALUATION_RUN")

    query = f"/audit-log?limit={limit}"
    if action_filter.strip():
        query += f"&action={action_filter.strip()}"
    payload = api_json("GET", query)
    if payload:
        st.dataframe(pd.DataFrame(payload), use_container_width=True)


def main() -> None:
    """Streamlit entrypoint."""
    st.set_page_config(page_title="AIALES", page_icon="A", layout="wide")
    apply_theme()
    init_state()

    if not st.session_state["access_token"] or not st.session_state["current_user"]:
        login_view()
        return

    classes = fetch_classes()
    page, selected_class_id, selected_experiment_id = render_sidebar(classes)

    if page == "Home":
        render_home(classes)
    elif page == "Workspace":
        render_workspace(selected_class_id, selected_experiment_id)
    elif page == "Users":
        render_users()


if __name__ == "__main__":
    main()
