import streamlit as st
from firebase_config import init_firestore
from auth_module import login_user
import pandas as pd

st.set_page_config(page_title="Reviewer Dashboard", layout="wide")
db = init_firestore()

# --- Authentication Check ---
if "authenticated_user" not in st.session_state or "user_role" not in st.session_state:
    login_user(db)
    st.stop()

if st.session_state["user_role"] != "reviewer":
    st.error("Access denied. Only reviewers can access this page.")
    st.stop()

# --- Force-clean navigation state on load ---
if "nav_stage" not in st.session_state:
    st.session_state.nav_stage = "list_users"
    st.session_state.selected_researcher = None
    st.session_state.selected_submission = None

st.title("📋 Reviewer Dashboard")

# --- Load all submissions grouped by researcher ---
@st.cache_data
def load_grouped():
    grouped = {}
    for doc in db.collection("submissions").stream():
        data = doc.to_dict()
        data["id"] = doc.id
        email = data.get("user_email", "unknown_user")
        grouped.setdefault(email, []).append(data)
    return grouped

grouped = load_grouped()

# --- Navigation States ---
if st.session_state.nav_stage == "list_users":
    st.subheader("👥 Researchers")
    for email, subs in grouped.items():
        total = len(subs)
        approved = sum(1 for s in subs if s.get("status") == "approved")
        rejected = sum(1 for s in subs if s.get("status") == "rejected")

        if st.button(f"{email} (Total: {total} | ✅ {approved} | ❌ {rejected})", key=f"user_{email}"):
            st.session_state.selected_researcher = email
            st.session_state.nav_stage = "list_submissions"
            st.rerun()

elif st.session_state.nav_stage == "list_submissions":
    email = st.session_state.selected_researcher
    user_subs = grouped[email]
    st.subheader(f"📄 Submissions from {email}")

    approved_subs = [s for s in user_subs if s.get("status") == "approved"]

    def flatten(subs):
        flat = []
        for s in subs:
            for eval in s.get("model_evaluations", []):
                flat.append({
                    "submission_id": s["id"],
                    "prompt": s["prompt"],
                    "system_prompt": s.get("system_prompt", ""),
                    "status": s.get("status", ""),
                    "model": eval.get("model", ""),
                    "response": eval.get("response", ""),
                    "token_usage": eval.get("token_usage", ""),
                    "model_break": eval.get("model_break", ""),
                    "model_break_comments": eval.get("model_break_comments", "")
                })
        return pd.DataFrame(flat)

    if approved_subs:
        df = flatten(approved_subs)
        st.download_button("📥 Download Approved Submissions", df.to_csv(index=False), file_name=f"{email}_approved.csv")

    for s in user_subs:
        sub_id = s["id"]
        status = s.get("status", "pending")
        color = "#28a745" if status == "approved" else "#dc3545" if status == "rejected" else "#FFA500"
        label = f"<span style='color:white;padding:4px;background:{color};border-radius:4px'>{status.upper()}</span>"

        col1, col2 = st.columns([5, 1])
        with col1:
            if st.button(f"View Submission {sub_id[:8]}", key=sub_id):
                st.session_state.selected_submission = sub_id
                st.session_state.nav_stage = "view_submission"
                st.rerun()
        with col2:
            st.markdown(label, unsafe_allow_html=True)

    if st.button("🔙 Back to Researchers"):
        st.session_state.nav_stage = "list_users"
        st.rerun()

elif st.session_state.nav_stage == "view_submission":
    sub_id = st.session_state.selected_submission
    doc = db.collection("submissions").document(sub_id).get()
    if not doc.exists:
        st.error("Submission not found.")
    else:
        data = doc.to_dict()
        st.subheader(f"🔍 Submission {sub_id}")
        st.markdown(f"**Submitted at:** {data.get('submitted_at', 'N/A')}")
        st.markdown(f"**System Prompt:** `{data.get('system_prompt', 'default')}`")
        st.markdown("#### Prompt")
        st.code(data["prompt"])

        st.markdown("### Model Evaluations")
        for eval in data.get("model_evaluations", []):
            st.markdown(f"**Model:** `{eval['model']}`")
            st.markdown(eval["response"])
            st.markdown(f"Tokens: {eval.get('token_usage', 'N/A')}")
            st.markdown(f"Break: {eval['model_break']}")
            if eval["model_break"] == "Yes":
                st.markdown(f"Comment: {eval.get('model_break_comments', '')}")
            st.markdown("---")

    if st.button("🔙 Back to Submission List"):
        st.session_state.nav_stage = "list_submissions"
        st.rerun()
