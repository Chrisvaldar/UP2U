import requests
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def test_places():
    url = "https://places.googleapis.com/v1/places:searchNearby"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.rating,places.formattedAddress",
    }

    body = {
        "includedTypes": ["restaurant"],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": -37.8136,  # Melbourne CBD
                    "longitude": 144.9631,
                },
                "radius": 500.0,  # 500 metres
            }
        },
    }

    response = requests.post(url, headers=headers, json=body)
    print(response.json())


def test_gemini():
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Say hello and tell me you are working correctly.",
    )
    print(response.text)


test_gemini()
