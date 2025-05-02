import openai
import requests
import streamlit as st

openai.api_key = st.secrets["OPENAI_KEY"]
GEMINI_KEY = st.secrets["GEMINI_KEY"]
DEEPSEEK_KEY = st.secrets["DEEPSEEK_KEY"]

def call_openai(model, system_prompt, prompt):
    response = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=1.0
    )
    return response.choices[0].message.content, response.usage.total_tokens

def call_gemini(model, system_prompt, prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}],
        "generationConfig": {"temperature": 1.0}
    }
    response = requests.post(url, headers=headers, params={"key": GEMINI_KEY}, json=payload)
    result = response.json()
    return result["candidates"][0]["content"]["parts"][0]["text"], None

def call_deepseek(model, system_prompt, prompt):
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_KEY}"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 1.0
    }
    response = requests.post(url, headers=headers, json=payload)
    result = response.json()
    content = result["choices"][0]["message"]["content"]
    return content, result.get("usage", {}).get("total_tokens")
