
import httpx
import json
from typing import AsyncGenerator
from app.core.config import get_settings

settings = get_settings()


# ---------------------------------------------------------------
# Ollama Client (local Mistral 7B)
# ---------------------------------------------------------------

async def ollama_generate(prompt: str, stream: bool = True) -> AsyncGenerator[str, None]:
    """
    Calls local Ollama API with Mistral 7B.
    Streams response tokens as they generate — makes 15s feel like 3s.

    # To switch model: change OLLAMA_MODEL in .env
    # e.g., OLLAMA_MODEL=llama3 or OLLAMA_MODEL=gemma2
    """
    url = f"{settings.ollama_base_url}/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": 0.3,        # Low temp = more consistent, less hallucination
            "num_predict": 512,        # Max tokens to generate (keep low for speed)
            "stop": ["</s>", "[/INST]"],  # Mistral stop tokens
        }
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        chunk = json.loads(line)
                        if chunk.get("response"):
                            yield chunk["response"]
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue


async def ollama_generate_full(prompt: str) -> str:
    """
    Non-streaming Ollama call — returns complete response string.
    Use for suggestions agent (one-shot, not chat).
    """
    result = []
    async for token in ollama_generate(prompt, stream=False):
        result.append(token)
    return "".join(result)


# ---------------------------------------------------------------
# Anthropic Client (Claude)
# Uncomment USE_OLLAMA=false and set ANTHROPIC_API_KEY in .env
# ---------------------------------------------------------------

async def anthropic_generate(prompt: str, stream: bool = True) -> AsyncGenerator[str, None]:
    """
    Calls Anthropic Claude API.
    # To activate: set USE_OLLAMA=false and ANTHROPIC_API_KEY in .env
    """
    # ---- UNCOMMENT THIS BLOCK TO USE ANTHROPIC ----
    # url = "https://api.anthropic.com/v1/messages"
    # headers = {
    #     "x-api-key": settings.anthropic_api_key,
    #     "anthropic-version": "2023-06-01",
    #     "content-type": "application/json",
    # }
    # payload = {
    #     "model": settings.anthropic_model,
    #     "max_tokens": 512,
    #     "stream": stream,
    #     "messages": [{"role": "user", "content": prompt}],
    # }
    # async with httpx.AsyncClient(timeout=60.0) as client:
    #     async with client.stream("POST", url, headers=headers, json=payload) as response:
    #         response.raise_for_status()
    #         async for line in response.aiter_lines():
    #             if line.startswith("data: "):
    #                 data = line[6:]
    #                 if data == "[DONE]": break
    #                 try:
    #                     chunk = json.loads(data)
    #                     delta = chunk.get("delta", {}).get("text", "")
    #                     if delta: yield delta
    #                 except json.JSONDecodeError: continue
    # ---- END ANTHROPIC BLOCK ----

    # Placeholder until activated
    yield "Anthropic API not configured. Set USE_OLLAMA=false and ANTHROPIC_API_KEY in .env."


# ---------------------------------------------------------------
# OpenAI Client
# Uncomment USE_OLLAMA=false and set OPENAI_API_KEY in .env
# ---------------------------------------------------------------

async def openai_generate(prompt: str, stream: bool = True) -> AsyncGenerator[str, None]:
    """
    Calls OpenAI API (gpt-4o-mini by default).
    # To activate: set USE_OLLAMA=false and OPENAI_API_KEY in .env
    """
    # ---- UNCOMMENT THIS BLOCK TO USE OPENAI ----
    # url = "https://api.openai.com/v1/chat/completions"
    # headers = {
    #     "Authorization": f"Bearer {settings.openai_api_key}",
    #     "Content-Type": "application/json",
    # }
    # payload = {
    #     "model": settings.openai_model,
    #     "max_tokens": 512,
    #     "stream": stream,
    #     "messages": [{"role": "user", "content": prompt}],
    # }
    # async with httpx.AsyncClient(timeout=60.0) as client:
    #     async with client.stream("POST", url, headers=headers, json=payload) as response:
    #         response.raise_for_status()
    #         async for line in response.aiter_lines():
    #             if line.startswith("data: "):
    #                 data = line[6:]
    #                 if data == "[DONE]": break
    #                 try:
    #                     chunk = json.loads(data)
    #                     delta = chunk["choices"][0]["delta"].get("content", "")
    #                     if delta: yield delta
    #                 except (json.JSONDecodeError, KeyError): continue
    # ---- END OPENAI BLOCK ----

    yield "OpenAI API not configured. Set USE_OLLAMA=false and OPENAI_API_KEY in .env."


# ---------------------------------------------------------------
# Router — picks provider based on .env
# ---------------------------------------------------------------

async def llm_stream(prompt: str) -> AsyncGenerator[str, None]:
    """
    Main entry point for streaming LLM calls.
    Reads USE_OLLAMA from settings and routes accordingly.
    """
    if settings.use_ollama:
        async for token in ollama_generate(prompt, stream=True):
            yield token
    elif settings.anthropic_api_key:
        async for token in anthropic_generate(prompt, stream=True):
            yield token
    elif settings.openai_api_key:
        async for token in openai_generate(prompt, stream=True):
            yield token
    else:
        yield "No LLM provider configured. Check .env file."


async def llm_complete(prompt: str) -> str:
    """
    Main entry point for non-streaming (full response) LLM calls.
    Used by suggestions agent.
    """
    if settings.use_ollama:
        return await ollama_generate_full(prompt)

    # ---- UNCOMMENT FOR ANTHROPIC (non-streaming) ----
    # elif settings.anthropic_api_key:
    #     result = []
    #     async for token in anthropic_generate(prompt, stream=False):
    #         result.append(token)
    #     return "".join(result)

    # ---- UNCOMMENT FOR OPENAI (non-streaming) ----
    # elif settings.openai_api_key:
    #     result = []
    #     async for token in openai_generate(prompt, stream=False):
    #         result.append(token)
    #     return "".join(result)

    return "No LLM provider configured. Check .env file."
