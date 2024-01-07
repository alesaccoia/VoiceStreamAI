import openai
import os


client = openai.Client(api_key="fake_key", base_url="http://vllm:8000/v1/")

def chat(text):
    return f"what do you mean by {text}"

    # response = client.chat.completions.create(
    #         model="/data0/model_output/shoppal-test/dreampal",
    #         messages= [{"role": "system", "content": "You are now a dream interpretation expert. Please analyze the description of the dream that I input."},
    #                    {"role": "user", "content": text }],
    #         # response_format={ "type": "json_object" },
    #         stream=False
    #     )

    # return response