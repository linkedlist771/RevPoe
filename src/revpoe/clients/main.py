import os
from openai import OpenAI

import json



client = OpenAI(
    # This is the default and can be omitted
    base_url="http://0.0.0.0:9002/v1",
    api_key=""
)
#
# chat_completion = client.chat.completions.create(
#     messages=[
#         {
#             "role": "user",
#             "content": "Say this is a test",
#         }
#     ],
#     model="gpt-3.5-turbo",
# )

stream = client.chat.completions.create(
    # model="gpt-4",
    model="Claude-3-Sonnet",
    messages=[{"role": "user", "content": "你是什么模型？"},
{"role": "assistant", "content": "你是什么模型？"},
{"role": "user", "content": "我上一句问了你什么？？"},
              ],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")

