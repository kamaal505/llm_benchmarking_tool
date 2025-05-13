import streamlit as st
from auth_module import login_user
from firebase_config import init_firestore
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="Reviewer Dashboard", layout="wide")

# --- Initialize Firestore ---
db = init_firestore()

# --- Authentication & Access Control ---
if "authenticated_user" not in st.session_state or "user_role" not in st.session_state:
    login_user(db)
    st.stop()

if st.session_state["user_role"] != "reviewer":
    st.error("Access denied. Only reviewers can access this page.")
    st.stop()

reviewer_email = st.session_state["authenticated_user"]
st.title("📋 Reviewer Dashboard")

# --- Filter by Submission Status ---
status_filter = st.selectbox("Filter submissions by status", ["All", "pending", "approved", "rejected"])

# --- Fetch Submissions from Firestore ---
query = db.collection("submissions")
if status_filter != "All":
    query = query.where("status", "==", status_filter)

submissions = query.order_by("submitted_at", direction="DESCENDING").stream()

# --- Render Submissions ---
for doc in submissions:
    data = doc.to_dict()
    doc_id = doc.id

    st.markdown("----")
    st.markdown(f"### 🧪 Prompt from `{data['user_email']}`")
    st.code(data["prompt"][:1000], language="text")

    st.write(f"**System Prompt:** `{data['system_prompt']}`")
    st.write(f"**Submitted At:** {data.get('submitted_at', 'N/A')}")
    st.write(f"**Current Status:** `{data.get('status', 'pending')}`")
    if data.get("reviewed_by"):
        st.write(f"**Reviewed By:** {data['reviewed_by']}")
    if data.get("reviewed_at"):
        st.write(f"**Reviewed At:** {data['reviewed_at']}")

    st.markdown("#### 📊 Model Evaluations")

    for eval in data.get("model_evaluations", []):
        st.markdown(f"**Model:** `{eval['model']}`")
        st.markdown("**Response:**")
        st.markdown(eval["response"])
        st.write(f"**Token Usage:** {eval.get('token_usage', 'N/A')}")
        st.write(f"**Model Break:** {eval['model_break']}")
        if eval["model_break"] == "Yes":
            st.write("**Break Comments:**", eval.get("model_break_comments", ""))
        st.markdown("---")

    # --- Review Controls ---
    st.markdown("#### 📝 Review Submission")

    status_options = ["pending", "approved", "rejected"]
    selected_status = st.radio("Set status", status_options,
                               index=status_options.index(data.get("status", "pending")),
                               key=f"status_{doc_id}")

    feedback = st.text_area("Reviewer Feedback (optional)",
                            value=data.get("reviewer_feedback", ""),
                            key=f"feedback_{doc_id}")

    if st.button(f"✅ Submit Review for {doc_id}"):
        db.collection("submissions").document(doc_id).update({
            "status": selected_status,
            "reviewer_feedback": feedback,
            "reviewed_by": reviewer_email,
            "reviewed_at": datetime.utcnow().isoformat()
        })
        st.success("Review submitted successfully!")
