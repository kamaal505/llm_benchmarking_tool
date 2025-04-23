import streamlit as st
import openai
import os
import re
import requests
from dotenv import load_dotenv
from streamlit.components.v1 import html
import firebase_admin
from firebase_admin import credentials, firestore
import json

try:
    from auth_module import login_user
except Exception as e:
    st.error(f"Failed to import login module: {e}")
    st.stop()

# Firebase initialization
if not firebase_admin._apps:
    firebase_json = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
    cred = credentials.Certificate(firebase_json)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_KEY") or st.secrets.get("OPENAI_KEY")
GEMINI_KEY = os.getenv("GEMINI_KEY") or st.secrets.get("GEMINI_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY") or st.secrets.get("DEEPSEEK_KEY")

# Page config
st.set_page_config(page_title="Benchmarking (Internal Testing)", layout="wide")

# Login
if "authenticated_user" not in st.session_state:
    login_user(db)
    st.stop()
else:
    user_email = st.session_state.authenticated_user

    # App UI starts here
    st.markdown("<h4>Benchmarking (Internal Testing)</h4>", unsafe_allow_html=True)

    default_system_prompt = """For Exact-Match Questions: Your response should be structured... [shortened for brevity]"""

    def render_inline_latex(text):
        container_style = """
            display: block;
            overflow-y: auto;
            max-height: 500px;
            padding: 1rem;
            margin-top: 0.5rem;
            border: 1px solid #444;
            background-color: #111;
        """
        text = re.sub(r'(\\\(.*?\\\))', r'\1', text)
        html_code = f"""
            <script type=\"text/javascript\" async
                src=\"https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js\">
            </script>
            <div style='{container_style}'>
                <p style='white-space: pre-wrap; margin: 0;'>{text}</p>
            </div>
        """
        html(html_code)

    st.markdown("<h4>Prompt</h4>", unsafe_allow_html=True)
    raw_prompt = st.text_area("", key="prompt_input", height=150)

    st.markdown("<h4>System Prompt</h4>", unsafe_allow_html=True)
    system_prompt_option = st.radio("Choose System Prompt", ["Default System Prompt", "Custom System Message"])
    if system_prompt_option == "Default System Prompt":
        with st.expander("View Default System Prompt", expanded=False):
            st.text_area("Default System Prompt", value=default_system_prompt, height=200, disabled=True, label_visibility="collapsed")
        system_prompt = default_system_prompt
    else:
        custom_prompt = st.text_area("Enter Custom System Message", key="custom_system", height=150)
        system_prompt = custom_prompt

    model_options = ["o1", "o3", "o4-mini", "gemini-2.5-pro-preview-03-25", "deepseek-reasoner", "All"]
    st.markdown("<h4>Choose model(s) to run</h4>", unsafe_allow_html=True)
    selected_models = st.multiselect("Select model(s) to run", model_options)

    if "All" in selected_models:
        models = [m for m in model_options if m != "All"]
    else:
        models = selected_models

    if st.button("Call LLM"):
        with st.spinner("Calling Model/s"):
            import concurrent.futures

            def fetch_response(model_name):
                try:
                    if model_name in ["o1", "o3", "o4-mini"]:
                        response = openai.chat.completions.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": raw_prompt}
                            ],
                            temperature=1.0
                        )
                        return model_name, response.choices[0].message.content, response.usage.total_tokens
                    elif model_name == "gemini-2.5-pro-preview-03-25":
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                        headers = {"Content-Type": "application/json"}
                        payload = {
                            "contents": [{"parts": [{"text": f"{system_prompt}\n\n{raw_prompt}"}]}],
                            "generationConfig": {"temperature": 1.0}
                        }
                        response = requests.post(url, headers=headers, params={"key": GEMINI_KEY}, json=payload)
                        result = response.json()
                        content = result["candidates"][0]["content"]["parts"][0]["text"]
                        return model_name, content, None
                    elif model_name == "deepseek-reasoner":
                        url = "https://api.deepseek.com/chat/completions"
                        headers = {
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {DEEPSEEK_KEY}"
                        }
                        payload = {
                            "model": model_name,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": raw_prompt}
                            ],
                            "temperature": 1.0
                        }
                        response = requests.post(url, headers=headers, json=payload)
                        result = response.json()
                        content = result["choices"][0]["message"]["content"]
                        return model_name, content, result.get("usage", {}).get("total_tokens", None)
                except Exception as e:
                    return model_name, f"Error: {str(e)}", None

            with concurrent.futures.ThreadPoolExecutor() as executor:
                st.session_state["model_results"] = list(executor.map(fetch_response, models))

    model_evaluations = []
    results = st.session_state.get("model_results", [])

    for model, reply, tokens in results:
        st.markdown(f"<h4>Model: `{model}`</h4>", unsafe_allow_html=True)

        if reply.startswith("Error:"):
            st.error(reply)
            continue

        st.markdown("<h4>Model Response</h4>", unsafe_allow_html=True)
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

    if results and st.button("Submit for Review"):
        try:
            submission = {
                "user_email": user_email,
                "prompt": raw_prompt,
                "system_prompt": system_prompt if system_prompt_option == "Custom System Message" else "default",
                "model_evaluations": model_evaluations,
                "submitted_at": firestore.SERVER_TIMESTAMP,
                "status": "pending"
            }
            doc_ref = db.collection("submissions").add(submission)
            st.success(f"Submission saved. ID: {doc_ref[1].id}")
        except Exception as e:
            st.error(f"Failed to submit: {e}")
