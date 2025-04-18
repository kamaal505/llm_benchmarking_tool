import streamlit as st
import openai
import os
import re
import requests
from dotenv import load_dotenv
from streamlit.components.v1 import html

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_KEY") or st.secrets.get("OPENAI_KEY")
GEMINI_KEY = os.getenv("GEMINI_KEY") or st.secrets.get("GEMINI_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY") or st.secrets.get("DEEPSEEK_KEY")

# Page config
st.set_page_config(page_title="Benchmarking (Internal Testing)", layout="wide")
st.markdown("<h4>Benchmarking (Internal Testing)</h4>", unsafe_allow_html=True)

# Default system prompt
default_system_prompt = """For Exact-Match Questions: Your response should be structured as follows to ensure clarity and adherence to the specified format. 

- Explanation: Provide a clear step-by-step explanation of your reasoning process, including all relevant mathematical computations formatted in LaTeX.

- Exact Answer: Present the final answer succinctly, ensuring it is precise and matches exactly what was requested.

- Confidence Score: Include a confidence score between 0% and 100%, reflecting your assurance in the accuracy of both your explanation and the exact answer provided.

For Multiple-Choice Questions (MCQs): Your response should be formatted as follows to accommodate each specific requirement. Include detailed explanations using LaTeX for mathematical workings where applicable.

- Explanation: Give an evaluation of all options, justifying why you selected a particular answer with clear reasoning.

- Answer Choice: Clearly state your chosen answer from the provided options. In case multiple options are correct, indicate those options in those answer choice.

- Confidence Score for Answer: Indicate your confidence level (between 0% and 100%) regarding selecting this specific answer choice based on your evaluation of all options."""

# Function to render inline LaTeX
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

# Prompt UI
st.markdown("<h4>Prompt</h4>", unsafe_allow_html=True)
raw_prompt = st.text_area("", key="prompt_input", height=150)

# System prompt UI
st.markdown("<h4>System Prompt</h4>", unsafe_allow_html=True)
system_prompt_option = st.radio("Choose System Prompt", ["Default System Prompt", "Custom System Message"])
if system_prompt_option == "Default System Prompt":
    with st.expander("View Default System Prompt", expanded=False):
        st.text_area("Default System Prompt", value=default_system_prompt, height=200, disabled=True, label_visibility="collapsed")
    system_prompt = default_system_prompt
else:
    custom_prompt = st.text_area("Enter Custom System Message", key="custom_system", height=150)
    system_prompt = custom_prompt

# Model selection
model_options = [
    "o1", "o3", "o4-mini",
    "gemini-2.5-pro-preview-03-25",
    "deepseek-reasoner", "All"
]
st.markdown("<h4>Choose model(s) to run</h4>", unsafe_allow_html=True)

selected_models = st.multiselect(
    "Select model(s) to run", 
    model_options,
)

if "All" in selected_models:
    models = [m for m in model_options if m != "All"]
else:
    models = selected_models

# Call LLMs
submit_button = st.button("Call LLM")

if submit_button:
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

    with st.spinner("Calling Model/s"):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(fetch_response, models))

    for model, reply, tokens in results:
        st.markdown(f"<h4>Model: `{model}`</h4>", unsafe_allow_html=True)
        if reply.startswith("Error:"):
            st.error(reply)
        else:
            st.markdown("<h4>Model Response</h4>", unsafe_allow_html=True)
            st.markdown(reply)
            if tokens is not None:
                st.markdown(f"**Token Usage:** {tokens} tokens")
            st.markdown("---")
