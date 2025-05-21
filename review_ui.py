import streamlit as st
from datetime import datetime

def render_model_responses(results):
    model_evaluations = []

    for model, reply, tokens in results:
        st.markdown(f"<h4>Model: `{model}`</h4>", unsafe_allow_html=True)

        if reply.startswith("Error:"):
            st.error(reply)
            continue

        st.markdown("#### Model Response")
        st.markdown(reply)

        if tokens is not None:
            st.markdown(f"**Token Usage:** {tokens} tokens")

        break_key = f"{model}_break"
        comment_key = f"{model}_comment"

        model_break = st.selectbox("Model Break Instance", ["No", "Yes"], key=break_key)

        model_break_comments = ""
        if model_break == "Yes":
            model_break_comments = st.text_area("Comments", key=comment_key)

        model_evaluations.append({
            "model": model,
            "response": reply,
            "token_usage": tokens,
            "model_break": model_break,
            "model_break_comments": model_break_comments
        })

        st.markdown("---")

    return model_evaluations

def submit_review(db, raw_prompt, system_prompt, prompt_mode, model_evaluations):
    # --- Ensure user is logged in and has correct role ---
    if "authenticated_user" not in st.session_state or "user_role" not in st.session_state:
        st.error("You must be logged in to submit.")
        return

    if st.session_state["user_role"] != "researcher":
        st.error("Only researchers can submit prompts.")
        return

    user_email = st.session_state["authenticated_user"]

    try:
        submission = {
            "user_email": user_email,
            "submitted_by_role": st.session_state["user_role"],
            "prompt": raw_prompt,
            "system_prompt": system_prompt if prompt_mode == "Custom System Message" else "default",
            "model_evaluations": model_evaluations,
            "submitted_at": datetime.utcnow().isoformat(),
            "status": "pending"
        }

        doc_ref = db.collection("submissions").add(submission)
        st.success(f"✅ Submission saved successfully. ID: `{doc_ref[1].id}`")

    except Exception as e:
        st.error(f"❌ Failed to submit: {e}")
