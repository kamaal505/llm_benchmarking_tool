import streamlit as st
from auth_module import login_user
from firebase_config import init_firestore
from prompts import default_prompt
from usage_logger import log_prompt_usage
from llm_runner import get_supported_models, run_models
from review_ui import render_model_responses, submit_review

# Streamlit Page Config
st.set_page_config(page_title="Benchmarking (Internal Testing)", layout="wide")

# Firebase Initialization
db = init_firestore()

# User Login
if "authenticated_user" not in st.session_state:
    login_user(db)
    st.stop()
user_email = st.session_state.authenticated_user

# --- UI Header ---
st.markdown("<h4>Benchmarking (Internal Testing)</h4>", unsafe_allow_html=True)

# --- Prompt Input ---
st.markdown("#### Prompt")
raw_prompt = st.text_area("", key="prompt_input", height=150)

# --- System Prompt Selection ---
st.markdown("#### System Prompt")
system_prompt_option = st.radio("Choose System Prompt", ["Default System Prompt", "Custom System Message"])
if system_prompt_option == "Default System Prompt":
    with st.expander("View Default System Prompt", expanded=False):
        st.text_area("Default System Prompt", value=default_prompt, height=200, disabled=True, label_visibility="collapsed")
    system_prompt = default_prompt
else:
    custom_prompt = st.text_area("Enter Custom System Message", key="custom_system", height=150)
    system_prompt = custom_prompt

# --- Model Selection ---
model_options = get_supported_models() + ["All"]
st.markdown("#### Choose model(s) to run")
selected_models = st.multiselect("Select model(s) to run", model_options)

if "All" in selected_models:
    models = [m for m in model_options if m != "All"]
else:
    models = selected_models

# --- Call LLM ---
if st.button("Call LLM"):
    with st.spinner("Calling Model/s"):
        st.session_state["model_results"] = run_models(models, system_prompt, raw_prompt)
        log_prompt_usage(db, user_email, raw_prompt, models)

# --- Display + Review ---
results = st.session_state.get("model_results", [])
if results:
    model_evaluations = render_model_responses(results)
    if st.button("Submit for Review"):
        submit_review(db, user_email, raw_prompt, system_prompt, system_prompt_option, model_evaluations)
