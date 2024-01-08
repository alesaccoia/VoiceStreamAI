import openai
import os


client = openai.Client(api_key="fake_key", base_url="http://10.232.14.16:8000/v1/")

def chat(text):
    response = client.chat.completions.create(
            model="/data0/models/huggingface/meta-llama/Llama-2-7b-chat-hf/",
            messages= [{"role": "system", "content": "you are a usefull agent and try to answer each question within 15 words"},
                       {"role": "user", "content": text }],
            # response_format={ "type": "json_object" },
            #stream=False
        )

    return response.choices[0].message.content

if __name__ == '__main__':
    ret = chat("hello")
    print(ret)