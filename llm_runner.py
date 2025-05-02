from llm_clients import call_openai, call_gemini, call_deepseek
import concurrent.futures

SUPPORTED_MODELS = {
    "o1": call_openai,
    "o3": call_openai,
    "o4-mini": call_openai,
    "gemini-2.5-pro-preview-03-25": call_gemini,
    "deepseek-reasoner": call_deepseek,
}

def get_supported_models():
    return list(SUPPORTED_MODELS.keys())

def run_models(models, system_prompt, user_prompt):
    def fetch_response(model_name):
        try:
            if model_name not in SUPPORTED_MODELS:
                raise ValueError(f"Unsupported model: {model_name}")
            response, tokens = SUPPORTED_MODELS[model_name](model_name, system_prompt, user_prompt)
            return model_name, response, tokens
        except Exception as e:
            return model_name, f"Error: {str(e)}", None

    with concurrent.futures.ThreadPoolExecutor() as executor:
        return list(executor.map(fetch_response, models))
