import streamlit as st
import openai
import os
import re
from dotenv import load_dotenv
from streamlit.components.v1 import html

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_KEY")

# Page config to move title to top-left
st.set_page_config(page_title="Benchmarking (OpenAI)", layout="wide")

st.markdown("<h4>Benchmarking (OpenAI)</h4>", unsafe_allow_html=True)

# Default system prompt
default_system_prompt = """
For Exact-Match Questions: Your response should be structured as follows to ensure clarity and adherence to the specified format. 

- Explanation: Provide a clear step-by-step explanation of your reasoning process, including all relevant mathematical computations formatted in LaTeX.

- Exact Answer: Present the final answer succinctly, ensuring it is precise and matches exactly what was requested.

- Confidence Score: Include a confidence score between 0% and 100%, reflecting your assurance in the accuracy of both your explanation and the exact answer provided.

For Multiple-Choice Questions (MCQs): Your response should be formatted as follows to accommodate each specific requirement. Include detailed explanations using LaTeX for mathematical workings where applicable.

- Explanation: Give an evaluation of all options, justifying why you selected a particular answer with clear reasoning.

- Answer Choice: Clearly state your chosen answer from the provided options. In case multiple options are correct, indicate those options in those answer choice.

- Confidence Score for Answer: Indicate your confidence level (between 0% and 100%) regarding selecting this specific answer choice based on your evaluation of all options.
"""

# Function to render inline LaTeX expressions within a sentence using MathJax

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
    text = re.sub(r'(\\(.*?\\))', r'\1', text)
    html_code = f"""
        <script type=\"text/javascript\" async
            src=\"https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js\">
        </script>
        <div style='{container_style}'>
            <p style='white-space: pre-wrap; margin: 0;'>{text}</p>
        </div>
    """
    html(html_code)

# Input prompt box
st.markdown("<h4>Prompt</h4>", unsafe_allow_html=True)
raw_prompt = st.text_area("", key="prompt_input", height=150)

# System prompt choice
st.markdown("<h4>System Prompt</h4>", unsafe_allow_html=True)
system_prompt_option = st.radio("Choose System Prompt", ["Default System Prompt", "Custom System Message"])

if system_prompt_option == "Default System Prompt":
    with st.expander("View Default System Prompt", expanded=False):
        st.text_area("Default System Prompt", value=default_system_prompt, height=200, disabled=True, label_visibility="collapsed", help="", key="default_display", args=(), kwargs={"style": {"color": "white"}})
    system_prompt = default_system_prompt
else:
    custom_prompt = st.text_area("Enter Custom System Message", key="custom_system", height=150)
    system_prompt = custom_prompt

# Model selection
st.markdown("<h4>Choose model(s) to run</h4>", unsafe_allow_html=True)
model_choice = st.selectbox("", ["o1", "o3-mini", "Both"])
models = ["o1", "o3-mini"] if model_choice == "Both" else [model_choice]

# Submit button
submit_button = st.button("Call LLM")

if submit_button:
    import concurrent.futures

    def fetch_response(model_name):
        try:
            response = openai.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": raw_prompt}
                ],
                temperature=1.0
            )
            return model_name, response
        except Exception as e:
            return model_name, f"Error: {str(e)}"

    with st.spinner("Calling Model/s"):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(fetch_response, models))

    for model, result in results:
        st.markdown(f"<h4>Model: `{model}`</h4>", unsafe_allow_html=True)
        if isinstance(result, str) and result.startswith("Error"):
            st.error(result)
        else:
            reply = result.choices[0].message.content
            usage = result.usage
            st.markdown("<h4>Model Response</h4>", unsafe_allow_html=True)
            st.markdown(reply)
            st.markdown(f"**Token Usage:** {usage.total_tokens} tokens")
            st.markdown("---")
