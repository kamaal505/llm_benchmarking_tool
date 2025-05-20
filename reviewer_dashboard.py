import streamlit as st
from firebase_config import init_firestore
from auth_module import login_user
from datetime import datetime
import pandas as pd

# --- Page Config ---
st.set_page_config(page_title="Reviewer Dashboard", layout="wide")
db = init_firestore()

# --- Auth Check ---
if "authenticated_user" not in st.session_state or "user_role" not in st.session_state:
    login_user(db)
    st.stop()

if st.session_state["user_role"] != "reviewer":
    st.error("Access denied. Only reviewers can access this page.")
    st.stop()

reviewer_email = st.session_state["authenticated_user"]
st.title("📋 Reviewer Dashboard")

# --- Helper Function ---
@st.cache_data
def load_submissions_grouped():
    submissions = db.collection("submissions").order_by("submitted_at", direction="DESCENDING").stream()
    grouped = {}

    for doc in submissions:
        data = doc.to_dict()
        user = data["user_email"]
        data["id"] = doc.id
        if user not in grouped:
            grouped[user] = []
        grouped[user].append(data)

    return grouped

grouped_submissions = load_submissions_grouped()

# --- Researcher List View ---
st.markdown("## 👥 Researchers")

for researcher_email, submissions in grouped_submissions.items():
    total = len(submissions)
    approved = sum(1 for s in submissions if s.get("status") == "approved")
    rejected = sum(1 for s in submissions if s.get("status") == "rejected")

    with st.expander(f"📧 {researcher_email} — Total: {total} | ✅ {approved} | ❌ {rejected}"):
        if st.button(f"📂 View submissions from {researcher_email}", key=f"view_{researcher_email}"):
            st.session_state["selected_researcher"] = researcher_email

# --- Submissions View ---
if "selected_researcher" in st.session_state:
    selected_email = st.session_state["selected_researcher"]
    st.markdown(f"## 📄 Submissions from `{selected_email}`")

    selected_subs = grouped_submissions[selected_email]

    approved_subs_for_download = []

    for sub in selected_subs:
        sub_id = sub["id"]
        status = sub.get("status", "pending")
        badge_color = "#28a745" if status == "approved" else "#dc3545" if status == "rejected" else "#FFA500"
        status_badge = f"<span style='color:white;padding:4px;border-radius:5px;background-color: {badge_color};'>{status.upper()}</span>"

        if st.button(f"📝 Submission ID: {sub_id[:8]}", key=sub_id):
            st.session_state["selected_submission"] = sub_id

        st.markdown(f"**Status:** {status_badge}", unsafe_allow_html=True)
        st.markdown("---")

        if status == "approved":
            approved_subs_for_download.append(sub)

    # Download button for approved submissions
    if approved_subs_for_download:
        def flatten(subs):
            flat = []
            for data in subs:
                for eval in data.get("model_evaluations", []):
                    flat.append({
                        "submission_id": data["id"],
                        "submitted_at": data.get("submitted_at", ""),
                        "status": data.get("status", ""),
                        "system_prompt": data.get("system_prompt", ""),
                        "prompt": data.get("prompt", ""),
                        "model": eval.get("model", ""),
                        "response": eval.get("response", ""),
                        "token_usage": eval.get("token_usage", ""),
                        "model_break": eval.get("model_break", ""),
                        "model_break_comments": eval.get("model_break_comments", "")
                    })
            return pd.DataFrame(flat)

        csv_df = flatten(approved_subs_for_download)
        st.download_button("📤 Download All Approved Submissions", data=csv_df.to_csv(index=False),
                           file_name=f"{selected_email}_approved.csv")

# --- Submission Detail View ---
if "selected_submission" in st.session_state:
    sub_id = st.session_state["selected_submission"]
    submission_doc = db.collection("submissions").document(sub_id).get()
    if submission_doc.exists:
        data = submission_doc.to_dict()

        st.markdown("## 🔍 Submission Detail")
        st.markdown(f"**Submission ID:** `{sub_id}`")
        st.write(f"Submitted At: {data.get('submitted_at', 'unknown')}")
        st.write(f"System Prompt: `{data.get('system_prompt', 'default')}`")
        st.markdown("#### Prompt:")
        st.code(data["prompt"], language="text")

        st.markdown("#### 📊 Model Evaluations")
        for eval in data.get("model_evaluations", []):
            st.markdown(f"**Model:** `{eval['model']}`")
            st.markdown("**Response:**")
            st.markdown(eval["response"])
            st.write(f"Token usage: {eval.get('token_usage', 'N/A')}")
            st.write(f"Model Break: {eval['model_break']}")
            if eval["model_break"] == "Yes":
                st.write(f"Break Comments: {eval.get('model_break_comments', '')}")
            st.markdown("---")
