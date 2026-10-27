

import ollama
import time

image_path = "receipts/receipt1_small.jpg"
start = time.time()

response = ollama.chat(
    model="qwen2.5vl:3b",
    messages=[{
        "role": "user",
        "content": "Read this receipt and write out all the text you can see.",
        "images": [image_path],
    }],
)

print(response["message"]["content"])
print(f"Took {time.time() - start:.1f} seconds for {image_path}")