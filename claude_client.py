import base64
import json
import config as c

categories = ["Groceries","Take out & restaurants","Going out","Clothing","Electronics","Home essentials","Medicine","Gifts","Transportation","Other"]
json_format = '{"store_name": "Lidl", "date":"2026-07-28", "items":{"Groceries": 34.50, "Clothing": 12.00}}'
apiRequest = f"Extract the place name and purchase date from the receipt image and only include:{categories} that had matching items, each with their total and format the result as a JSON  and Format date as 'YYYY-MM-DD', it should somthing like this {json_format}"

def scan_receipt_image(file) :
    image_bytes = file.read()
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    media_type = file.mimetype

    message = c.anthropic.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": apiRequest,
                    },
                ],
            }
        ],
    )

    response_text = message.content[0].text
    response_text = response_text.replace("```json","")
    response_text = response_text.replace("```","")  
    response_text = response_text.strip()
    parsed = json.loads(response_text)
    return parsed 