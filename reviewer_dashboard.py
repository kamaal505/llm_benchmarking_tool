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

# --- Group submissions by researcher ---
@st.cache_data
def get_submissions_by_user():
    submissions = db.collection("submissions").order_by("submitted_at", direction="DESCENDING").stream()
    grouped = {}

    for doc in submissions:
        data = doc.to_dict()
        user = data["user_email"]
        if user not in grouped:
            grouped[user] = []
        grouped[user].append((doc.id, data))

    return grouped

submissions_by_user = get_submissions_by_user()

# --- Researcher selection ---
st.markdown("### Researchers with submissions")
selected_email = st.selectbox("Select a researcher to view submissions", list(submissions_by_user.keys()))

if selected_email:
    user_submissions = submissions_by_user[selected_email]

    # --- CSV Export Button ---
    def to_flat_records(submissions):
        flat = []
        for doc_id, data in submissions:
            for eval in data.get("model_evaluations", []):
                flat.append({
                    "submission_id": doc_id,
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

    csv_data = to_flat_records(user_submissions)
    st.download_button("📤 Export All Submissions to CSV", data=csv_data.to_csv(index=False), file_name=f"{selected_email}_submissions.csv")

    # --- Submissions table ---
    st.markdown(f"### 📄 Submissions from `{selected_email}`")

    for doc_id, data in user_submissions:
        submitted_at = data.get("submitted_at", "unknown")
        status = data.get("status", "pending")
        short_id = doc_id[:8]
        submitted_time = submitted_at.split("T")[0] if isinstance(submitted_at, str) else submitted_at

        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            st.markdown(f"**ID:** `{short_id}`")
        with col2:
            st.markdown(f"**Submitted:** {submitted_time}")
        with col3:
            status_badge = f"<span style='color:white;padding:4px;border-radius:5px;background-color: {'#FFA500' if status=='pending' else ('#28a745' if status=='approved' else '#dc3545')};'>{status.upper()}</span>"
            st.markdown(f"**Status:** {status_badge}", unsafe_allow_html=True)

        with st.expander("🔍 View Full Submission"):
            st.code(data["prompt"], language="text")
            st.write(f"System Prompt: `{data.get('system_prompt', 'default')}`")

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

        st.markdown("------")
