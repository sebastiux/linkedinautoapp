'''
Claude (Anthropic) AI provider connector.

Mirrors the structure of the other providers (openai / deepseek / gemini) but
uses Anthropic's native `anthropic` SDK and Messages API.

Install the SDK with:  pip install anthropic
Get an API key at:      https://console.anthropic.com/
'''

from config.secrets import *
from config.settings import showAiErrorAlerts
from modules.helpers import print_lg, critical_error_log, convert_to_json
from modules.ai.prompts import *

from pyautogui import confirm
from typing import Literal

try:
    from anthropic import Anthropic
except Exception:
    Anthropic = None


# Default token budget for a single completion
CLAUDE_MAX_TOKENS = 4096


def claude_create_client() -> "Anthropic | None":
    '''
    Creates an Anthropic (Claude) client.
    * Returns an `Anthropic` client, or `None` if creation fails.
    '''
    global showAiErrorAlerts
    try:
        print_lg("Creating Claude (Anthropic) client...")
        if not use_AI:
            raise ValueError("AI is not enabled! Please enable it by setting `use_AI = True` in `secrets.py` in `config` folder.")
        if Anthropic is None:
            raise ImportError("The `anthropic` package is not installed. Run `pip install anthropic`.")
        if not llm_api_key or llm_api_key in ("", "not-needed", "YOUR_API_KEY"):
            raise ValueError("Claude API key is not set. Please set `llm_api_key` in `config/secrets.py`.")

        # `llm_api_url` is optional for Claude; only pass it if a custom one is provided
        kwargs = {"api_key": llm_api_key}
        default_url = "https://api.anthropic.com"
        if llm_api_url and default_url not in llm_api_url and "openai.com" not in llm_api_url:
            kwargs["base_url"] = llm_api_url.rstrip("/")

        client = Anthropic(**kwargs)

        print_lg("---- SUCCESSFULLY CREATED CLAUDE CLIENT! ----")
        print_lg(f"Using Model: {llm_model}")
        print_lg("Check './config/secrets.py' for more details.\n")
        print_lg("---------------------------------------------")
        return client
    except Exception as e:
        error_message = "Error occurred while creating Claude client. Make sure your API key and model name are correct."
        critical_error_log(error_message, e)
        if showAiErrorAlerts:
            if "Pause AI error alerts" == confirm(f"{error_message}\n{str(e)}", "Claude Connection Error", ["Pause AI error alerts", "Okay Continue"]):
                showAiErrorAlerts = False
        return None


def claude_completion(client: "Anthropic", messages: list[dict], system: str = None, temperature: float = 0, stream: bool = stream_output, expecting_json: bool = False) -> dict | str:
    '''
    Completes a chat using the Claude Messages API.
    * `client` - The Anthropic client
    * `messages` - The conversation messages (list of {"role", "content"})
    * `system` - Optional system prompt
    * `temperature` - Randomness control (default 0)
    * `stream` - Whether to stream the output
    * `expecting_json` - If True, the result is parsed into JSON
    * Returns the response as text or JSON
    '''
    if not client:
        raise ValueError("Claude client is not available!")

    params = {
        "model": llm_model,
        "max_tokens": CLAUDE_MAX_TOKENS,
        "temperature": temperature,
        "messages": messages,
    }
    if system:
        params["system"] = system

    try:
        print_lg("Calling Claude API for completion...")
        print_lg(f"Using model: {llm_model}")
        print_lg(f"Message count: {len(messages)}")
        result = ""

        if stream:
            print_lg("--STREAMING STARTED")
            with client.messages.stream(**params) as stream_resp:
                for text in stream_resp.text_stream:
                    result += text
                    print_lg(text, end="", flush=True)
            print_lg("\n--STREAMING COMPLETE")
        else:
            completion = client.messages.create(**params)
            result = "".join(
                block.text for block in completion.content if getattr(block, "type", None) == "text"
            )

        if expecting_json:
            result = convert_to_json(result)

        print_lg("\nClaude Answer:\n")
        print_lg(result, pretty=expecting_json)
        return result
    except Exception as e:
        error_message = f"Claude API error: {str(e)}"
        print_lg(f"Full error details: {e.__class__.__name__}: {str(e)}")
        if "Connection" in str(e):
            print_lg("This might be a network issue. Please check your internet connection.")
        elif "401" in str(e) or "authentication" in str(e).lower():
            print_lg("This appears to be an authentication error. Your API key might be invalid or expired.")
        elif "404" in str(e) or "not_found" in str(e).lower():
            print_lg("The requested model could not be found. Check `llm_model` in `config/secrets.py`.")
        elif "429" in str(e):
            print_lg("You've exceeded the rate limit. Please wait before making more requests.")
        raise ValueError(error_message)


def claude_extract_skills(client: "Anthropic", job_description: str, stream: bool = stream_output) -> dict | ValueError:
    '''
    Extracts skills from a job description using Claude.
    * `client` - The Anthropic client
    * `job_description` - The job description text
    * Returns a `dict` representing the JSON response
    '''
    try:
        print_lg("Extracting skills from job description using Claude...")
        prompt = deepseek_extract_skills_prompt.format(job_description)
        messages = [{"role": "user", "content": prompt}]
        system = "You are a helpful assistant. Respond ONLY with a valid JSON object, no markdown fences or extra text."

        result = claude_completion(
            client=client,
            messages=messages,
            system=system,
            stream=stream,
            expecting_json=True,
        )
        if isinstance(result, str):
            result = convert_to_json(result)
        return result
    except Exception as e:
        critical_error_log("Error occurred while extracting skills with Claude!", e)
        return {"error": str(e)}


def claude_answer_question(
    client: "Anthropic",
    question: str, options: list[str] | None = None,
    question_type: Literal['text', 'textarea', 'single_select', 'multiple_select'] = 'text',
    job_description: str = None, about_company: str = None, user_information_all: str = None,
    stream: bool = stream_output
) -> dict | ValueError:
    '''
    Answers an application question using Claude.
    * `client` - The Anthropic client
    * `question` - The question to answer
    * `options` - Options for select questions
    * `question_type` - text, textarea, single_select or multiple_select
    * Optional context - job_description, about_company, user_information_all
    * Returns the AI's answer
    '''
    try:
        print_lg(f"Answering question using Claude AI: {question}")
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
        result = claude_completion(
            client=client,
            messages=messages,
            temperature=0.1,
            stream=stream,
        )
        return result
    except Exception as e:
        critical_error_log("Error occurred while answering question with Claude!", e)
        return {"error": str(e)}


def claude_close_client(client: "Anthropic") -> None:
    '''
    Closes the Claude client (no-op for the Anthropic SDK, kept for symmetry).
    '''
    try:
        if client and hasattr(client, "close"):
            client.close()
    except Exception:
        pass
