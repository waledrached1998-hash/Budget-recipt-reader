import base64
import json
import config as c
from db import get_categories

categories = ["Groceries","Take out & restaurants","Going out","Clothing","Electronics","Home essentials","Medicine","Gifts","Transportation","Other"]



def build_prompt(user_id):
    categories = get_categories(user_id)
    json_format_true = '{"is_receipt": true, "store_name": "Lidl", "date": "2026-07-28", "items": {"Groceries": 34.50, "Clothing": 12.00}}'
    json_format_false = '{"is_receipt": false}'

    apiRequest = f"""You will be shown an image. Follow these steps in order:

    1. First, determine whether the image is a real receipt or invoice showing a purchase.
    2. If it is NOT a receipt or invoice, respond with exactly this JSON and nothing else:
    {json_format_false}
    3. If it IS a receipt or invoice, extract:
    - The store or merchant name
    - The purchase date, converted to YYYY-MM-DD format (not the format printed on the receipt)
    - Every item's cost grouped into these categories, only including categories that had a matching item: {categories}

    Respond with ONLY valid JSON, no other text, no markdown code fences, matching this exact shape:
    {json_format_true}

    Return nothing except one of these two JSON shapes."""

    return apiRequest


def scan_receipt_image(file,user_id) :
    apiRequest = build_prompt(user_id)
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