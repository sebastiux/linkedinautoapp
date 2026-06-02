'''
Grok (xAI) AI provider connector.

Grok exposes an OpenAI-compatible API, so this reuses the `openai` SDK pointed
at xAI's endpoint (https://api.x.ai/v1), mirroring the DeepSeek connector.

Get an API key at: https://console.x.ai/
'''

from config.secrets import *
from config.settings import showAiErrorAlerts
from modules.helpers import print_lg, critical_error_log, convert_to_json
from modules.ai.prompts import *

from pyautogui import confirm
from openai import OpenAI
from typing import Literal


# Default xAI endpoint, used when no custom/compatible URL is configured
GROK_DEFAULT_URL = "https://api.x.ai/v1"


def grok_create_client() -> OpenAI | None:
    '''
    Creates a Grok (xAI) client using the OpenAI compatible API.
    * Returns an OpenAI-compatible client configured for xAI, or None on failure.
    '''
    global showAiErrorAlerts
    try:
        print_lg("Creating Grok (xAI) client...")
        if not use_AI:
            raise ValueError("AI is not enabled! Please enable it by setting `use_AI = True` in `secrets.py` in `config` folder.")
        if not llm_api_key or llm_api_key in ("", "not-needed", "YOUR_API_KEY"):
            raise ValueError("Grok API key is not set. Please set `llm_api_key` in `config/secrets.py`.")

        # Use the configured URL, but fall back to xAI's endpoint if the default
        # OpenAI/Anthropic URLs are still set.
        base_url = llm_api_url.rstrip("/") if llm_api_url else ""
        if not base_url or "openai.com" in base_url or "anthropic.com" in base_url:
            base_url = GROK_DEFAULT_URL

        client = OpenAI(base_url=base_url, api_key=llm_api_key)

        print_lg("---- SUCCESSFULLY CREATED GROK CLIENT! ----")
        print_lg(f"Using API URL: {base_url}")
        print_lg(f"Using Model: {llm_model}")
        print_lg("Check './config/secrets.py' for more details.\n")
        print_lg("---------------------------------------------")
        return client
    except Exception as e:
        error_message = "Error occurred while creating Grok client. Make sure your API key and model name are correct."
        critical_error_log(error_message, e)
        if showAiErrorAlerts:
            if "Pause AI error alerts" == confirm(f"{error_message}\n{str(e)}", "Grok Connection Error", ["Pause AI error alerts", "Okay Continue"]):
                showAiErrorAlerts = False
        return None


def grok_completion(client: OpenAI, messages: list[dict], response_format: dict = None, temperature: float = 0, stream: bool = stream_output) -> dict | str:
    '''
    Completes a chat using the Grok (xAI) API and formats the result.
    * `client` - The Grok client
    * `messages` - The conversation messages
    * `response_format` - Optional dict for JSON output
    * `temperature` - Randomness control (default 0)
    * `stream` - Whether to stream the output
    * Returns the response as text or JSON
    '''
    if not client:
        raise ValueError("Grok client is not available!")

    params = {
        "model": llm_model,
        "messages": messages,
        "temperature": temperature,
        "stream": stream,
        "timeout": 30,
    }
    if response_format:
        params["response_format"] = response_format

    try:
        print_lg("Calling Grok API for completion...")
        print_lg(f"Using model: {llm_model}")
        print_lg(f"Message count: {len(messages)}")
        try:
            completion = client.chat.completions.create(**params)
        except Exception as inner:
            # Some xAI models (e.g. reasoning models) reject `temperature`. Drop it and retry.
            if "temperature" in str(inner).lower():
                print_lg("This model doesn't accept 'temperature'; retrying without it...")
                params.pop("temperature", None)
                completion = client.chat.completions.create(**params)
            else:
                raise
        result = ""

        if stream:
            print_lg("--STREAMING STARTED")
            for chunk in completion:
                if chunk.model_extra and chunk.model_extra.get("error"):
                    raise ValueError(f'Error occurred with Grok API: "{chunk.model_extra.get("error")}"')
                chunk_message = chunk.choices[0].delta.content
                if chunk_message is not None:
                    result += chunk_message
                print_lg(chunk_message, end="", flush=True)
            print_lg("\n--STREAMING COMPLETE")
        else:
            if completion.model_extra and completion.model_extra.get("error"):
                raise ValueError(f'Error occurred with Grok API: "{completion.model_extra.get("error")}"')
            result = completion.choices[0].message.content

        if response_format:
            result = convert_to_json(result)

        print_lg("\nGrok Answer:\n")
        print_lg(result, pretty=response_format is not None)
        return result
    except Exception as e:
        error_message = f"Grok API error: {str(e)}"
        print_lg(f"Full error details: {e.__class__.__name__}: {str(e)}")
        if "Connection" in str(e):
            print_lg("This might be a network issue. Please check your internet connection.")
        elif "401" in str(e):
            print_lg("This appears to be an authentication error. Your API key might be invalid or expired.")
        elif "404" in str(e):
            print_lg("The requested resource could not be found. The API URL or model name might be incorrect.")
        elif "429" in str(e):
            print_lg("You've exceeded the rate limit. Please wait before making more requests.")
        raise ValueError(error_message)


def grok_extract_skills(client: OpenAI, job_description: str, stream: bool = stream_output) -> dict | ValueError:
    '''
    Extracts skills from a job description using Grok.
    * `client` - The Grok client
    * `job_description` - The job description text
    * Returns a `dict` representing the JSON response
    '''
    try:
        print_lg("Extracting skills from job description using Grok...")
        prompt = deepseek_extract_skills_prompt.format(job_description)
        messages = [{"role": "user", "content": prompt}]
        custom_response_format = {"type": "json_object"}

        result = grok_completion(
            client=client,
            messages=messages,
            response_format=custom_response_format,
            stream=stream,
        )
        if isinstance(result, str):
            result = convert_to_json(result)
        return result
    except Exception as e:
        critical_error_log("Error occurred while extracting skills with Grok!", e)
        return {"error": str(e)}


def grok_answer_question(
    client: OpenAI,
    question: str, options: list[str] | None = None,
    question_type: Literal['text', 'textarea', 'single_select', 'multiple_select'] = 'text',
    job_description: str = None, about_company: str = None, user_information_all: str = None,
    stream: bool = stream_output
) -> dict | ValueError:
    '''
    Answers an application question using Grok.
    * `client` - The Grok client
    * `question` - The question to answer
    * `options` - Options for select questions
    * `question_type` - text, textarea, single_select or multiple_select
    * Optional context - job_description, about_company, user_information_all
    * Returns the AI's answer
    '''
    try:
        print_lg(f"Answering question using Grok AI: {question}")
        user_info = user_information_all or ""
        prompt = ai_answer_prompt.format(user_info, question)

        if options and (question_type in ['single_select', 'multiple_select']):
            options_str = "OPTIONS:\n" + "\n".join([f"- {option}" for option in options])
            prompt += f"\n\n{options_str}"
            if question_type == 'single_select':
                prompt += "\n\nPlease select exactly ONE option from the list above."
            else:
                prompt += "\n\nYou may select MULTIPLE options from the list above if appropriate."

        if job_description:
            prompt += f"\n\nJOB DESCRIPTION:\n{job_description}"
        if about_company:
            prompt += f"\n\nABOUT COMPANY:\n{about_company}"

        messages = [{"role": "user", "content": prompt}]
        result = grok_completion(
            client=client,
            messages=messages,
            temperature=0.1,
            stream=stream,
        )
        return result
    except Exception as e:
        critical_error_log("Error occurred while answering question with Grok!", e)
        return {"error": str(e)}


def grok_generate_resume(client: OpenAI, job_description: str, master_resume_latex: str) -> str | None:
    '''
    Asks Grok to tailor `master_resume_latex` to `job_description`.
    Returns the tailored LaTeX source, or None on failure.
    '''
    try:
        print_lg("Generating a tailored resume with Grok...")
        prompt = resume_generation_prompt.format(master_resume_latex, job_description)
        messages = [
            {"role": "system", "content": "You are an expert resume writer and LaTeX engineer. Output ONLY valid LaTeX (no markdown fences, no commentary)."},
            {"role": "user", "content": prompt},
        ]
        result = grok_completion(client, messages, temperature=0.2, stream=False)
        return result if isinstance(result, str) else None
    except Exception as e:
        critical_error_log("Error generating tailored resume with Grok!", e)
        return None
