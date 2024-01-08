import openai

import os

api_key = "fake_key"
api_base = "http://vllm:8000/v1/"
client = openai.Client(api_key=api_key, base_url=api_base)

model_name = "/data0/model_output/shoppal-test/dreampal"

def predict(message, history, system_prompt):
    history_openai_format = []
    history_openai_format.append({"role": "system", "content": system_prompt})
    for human, assistant in history:
        history_openai_format.append({"role": "user", "content": human })
        history_openai_format.append({"role": "assistant", "content":assistant})
    history_openai_format.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model=model_name,
        messages= history_openai_format,
        # response_format={ "type": "json_object" },
        stream=True
    )

    partial_message = ""
    for chunk in response:
        if chunk.choices[0].delta.content and len(chunk.choices[0].delta.content) != 0:
            partial_message = partial_message + chunk.choices[0].delta.content
            yield partial_message

system_prompt = """
You are now a dream interpretation expert. Please analyze the description of the dream that I input.
"""

response = client.chat.completions.create(
        model=model_name,
        messages= [{"role": "system", "content": system_prompt},
                   {"role": "user", "content": "hello" }],
        #sresponse_format={ "type": "json_object" },
        #stream=False
    )

#print(response.choices[0].message)