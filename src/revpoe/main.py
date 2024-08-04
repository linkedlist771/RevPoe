import os

DEFAULT_MODEL = os.getenv("BOT", default="Claude-3-Sonnet")
LISTEN_PORT = int(os.getenv("PORT", default=9002))
BASE_URL = os.getenv("BASE", default="https://api.poe.com/bot/")

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

import uvicorn
from typing import AsyncGenerator
import json

from fastapi_poe.types import ProtocolMessage
from fastapi_poe.client import get_bot_response

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"])


async def generate_responses(api_key: str, formatted_messages: list, bot_name: str) -> AsyncGenerator[str, None]:
    """An async generator to stream responses from the POE API."""

    # Create a base response template
    response_template = {
        "id": "chatcmpl-123",
        "object": "chat.completion.chunk",
        "created": 1694268190,
        "model": "gpt-4",
        "choices": [{
            "index": 0,
            "delta": {
                "content": "",  # Placeholder, to be filled for each partial response
                "logprobs": None,
                "finish_reason": None
            }
        }]
    }

    async for partial in get_bot_response(messages=formatted_messages, bot_name=bot_name, api_key=api_key,
                                          base_url=BASE_URL,
                                          skip_system_prompt=False,
                                          logit_bias={'24383': -100}):
        # Fill the required field for this partial response
        response_template["choices"][0]["delta"]["content"] = partial.text

        # Create the SSE formatted string, and then yield
        yield f"data: {json.dumps(response_template)}\n\n"

    # Send termination sequence
    response_template["choices"][0]["delta"] = {}  # Empty 'delta' field
    response_template["choices"][0]["finish_reason"] = "stop"  # Set 'finish_reason' to 'stop'

    yield f"data: {json.dumps(response_template)}\n\ndata: [DONE]\n\n"


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")

    api_key = authorization.split(" ")[1]  # Assuming the header follows the standard format: "Bearer $API_KEY"
    body = await request.json()

    # Extract bot_name (model) and messages from the request body
    bot_name = body.get("model", DEFAULT_MODEL)  # Defaulting to a specific bot if not provided
    messages = body.get("messages", [])

    formatted_messages = [ProtocolMessage(role=msg["role"].lower().replace("assistant", "bot"),
                                          content=msg["content"],
                                          temperature=msg.get("temperature", 0.95))
                          for msg in messages]

    async def response_stream() -> AsyncGenerator[str, None]:
        async for response_content in generate_responses(api_key, formatted_messages, bot_name):
            # Assuming each response_content is a complete "message" response from the bot.
            # Adjust according to actual response pattern if needed.
            yield response_content

    # Stream responses back to the client
    # Wrap the streamed content to fit the desired response format
    return StreamingResponse(response_stream(), media_type="application/json")


if __name__ == '__main__':
    try:
        import uvloop
    except ImportError:
        uvloop = None
    if uvloop:
        uvloop.install()
    uvicorn.run(app, host="0.0.0.0", port=LISTEN_PORT)