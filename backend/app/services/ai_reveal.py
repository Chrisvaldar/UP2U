import json
from google import genai
from google.genai.errors import ClientError, ServerError
from groq import Groq, APIError

from app import config
from app import errors
from app import utils
from app.services import photos
from app.services import places
from app.services import ranking


def run_reveal_pipeline(users: list[dict], latitude: float, longitude: float) -> dict:
    """
    Run the full reveal pipeline from user answers to an AI-generated reveal.

    Args:
        users: Participant answer dicts with preferences and travel_distance.
        latitude: Session location latitude.
        longitude: Session location longitude.

    Returns:
        A reveal dict from generate_reveal with personality lines, agreements,
        conflicts, primary restaurant, backups, and photo URLs.
    """
    radius = ranking.get_search_radius(users)
    restaurants = places.get_nearby_restaurants(latitude, longitude, 2000)
    shortlist = ranking.rank_restaurants_for_group(restaurants, radius, users)
    return generate_reveal(users, shortlist, radius)


def _gemini_is_rate_limited(exc: Exception) -> bool:
    """
    Detect whether a Gemini client error indicates rate limiting or overload.

    Args:
        exc: Exception raised by the Gemini client.

    Returns:
        True if exc is a ClientError or ServerError with code 429 or 503.
    """
    if isinstance(exc, (ClientError, ServerError)):
        return exc.code in (429, 503)
    return False


def call_gemini(system_prompt: str, user_prompt: str) -> str:
    """
    Generate reveal content using the Gemini API.

    Args:
        system_prompt: System instruction defining tone and JSON output rules.
        user_prompt: User message with group preferences and restaurant data.

    Returns:
        Stripped text content from the Gemini model response.
    """
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config={"system_instruction": system_prompt},
        contents=user_prompt,
    )
    return response.text.strip()


def call_groq(system_prompt: str, user_prompt: str) -> str:
    """
    Generate reveal content using the Groq API as a Gemini fallback.

    Args:
        system_prompt: System message defining tone and JSON output rules.
        user_prompt: User message with group preferences and restaurant data.

    Returns:
        Stripped text content from the Groq chat completion.

    Raises:
        UpstreamUnavailable: On Groq rate limit (429) or overload (503).
        UpstreamBadResponse: On other Groq API errors.
    """
    try:
        client = Groq(api_key=config.GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content.strip()
    except APIError as e:
        status = getattr(e, "status_code", None)
        config.logger.exception(f"Groq call failed status={status}")

        # 429 = rate limited, 503 = temporarily overloaded
        if status in (429, 503):
            raise errors.UpstreamUnavailable(f"groq status={status}") from e
        raise errors.UpstreamBadResponse(f"groq status={status}") from e


def parse_reveal_response(raw: str) -> dict:
    """
    Parse raw AI output into a reveal dict, stripping markdown fences if present.

    Args:
        raw: Raw model output, optionally wrapped in ```json code fences.

    Returns:
        Parsed reveal dict with personality_lines, agreements, conflicts,
        primary, and backups keys.

    Raises:
        UpstreamBadResponse: If the content is not valid JSON.
    """
    try:
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        config.logger.error(f"Failed to parse reveal JSON: {utils.truncate_log(raw)}")
        raise errors.UpstreamBadResponse("reveal AI returned invalid JSON") from e


def generate_reveal(users: list[dict], restaurants: list[dict], strict_radius: int):
    """
    Build prompts, call Gemini (with Groq fallback), and enrich the reveal with photos.

    Args:
        users: Participant answer dicts formatted into the user prompt.
        restaurants: Ranked restaurant shortlist; only the first 15 are sent to the model.
        strict_radius: Maximum travel distance in metres included in the prompt.

    Returns:
        Parsed and photo-enriched reveal dict ready for the client.

    Raises:
        UpstreamUnavailable: When Gemini or Groq is rate limited or overloaded.
        UpstreamBadResponse: When the model call fails or returns invalid JSON.
    """
    restaurants = restaurants[:15]

    # Format user preferences as a readable block for the prompt
    preferences_text = "\n".join(
        f"{u['name']}: hunger={u['hunger']}, vibe={u['vibe']}, "
        f"cuisines={u['cuisines_ranked']}, travel_distance={u['travel_distance']}, "
        f"dietary={u['dietary']}"
        for u in users
    )

    # Format restaurant data as a readable block for the prompt
    restaurants_text = "\n".join(
        f"{r['name']}: cuisines={r['cuisines']}, rating={r['rating']} "
        f"({r['review_count']} reviews), price_level={r['price_level']}, "
        f"distance_meters={r['distance_meters']}, open_now={r['open_now']}, "
        f"summary={r['summary']}, address={r['address']}, maps_link={r['maps_link']}"
        for r in restaurants
    )

    system_prompt = """You are a fun, hype-man AI helping a group of friends decide where to eat.
You're part of the group, not an outsider observing them. Only pick from the restaurant's list, don't invent places

Your job:
1. Write a SHORT roast-style personality line for each person based on their food mood
2. Summarise what the group agrees on and where they clash
3. Pick the single best restaurant and hype it up
4. Provide 2 backup options with punchy reasons

Rules for personality lines, agreements, and conflicts (all use the same newline rules):
- Each sentence is at most 10 words (count before writing). Emoji counts as part of that sentence — keep emoji at the END of the sentence, same line.
- A sentence must be complete before you add \\n. NEVER put \\n in the middle of a sentence.
- NEVER put an emoji alone on its own line. NEVER split "text\\n🌶️" or "word\\nrest of sentence".
- Use \\n ONLY between separate complete sentences (each ≤10 words).
- If one sentence is enough, do not add \\n at all.
- Roast-style but friendly for personality lines; roast behaviour, not preferences
- Use deadpan humour, not just exclamation marks
- Talk TO the group directly, not about them

Personality line examples (GOOD — each line is one full sentence):
- "Someone REALLY needs their Thai fix 🌶️"
- "Apparently salads count as a meal 🥗"
- "Would eat anything right now 🤤\\nAbsolutely no standards detected 😌"

Personality line examples (BAD — do not do this):
- "Would eat anything\\nright now 🤤" (splits mid-sentence)
- "Thai fix 🌶️\\n🌶️" (emoji alone on a line)
- "Everyone wants casual vibes and also\\nnobody wants to walk far" (splits one sentence)

Rules for agreements and conflicts:
- Speak as part of the group — use "everyone", "most of us", "almost everyone"
- NEVER say "they both" or "they" — you are IN the group
- Make it fun — emoji at end of sentence, same line
- Example agreements: "Everyone's down for Indian and Mexican 🌶️\\nNobody wants to walk far today 👣"
- Example conflicts: "Half of us want quick bites 🏃\\nThe other half want a vibe 👀"

Rules for primary reason:
- 2 sentences max, hype it up like you're genuinely excited
- Explain why it works for THIS specific group

Rules for backup reasons:
- 1 sentence, punchy

Other rules:
- Respect dietary restrictions strictly, never recommend somewhere a person can't eat
- Never recommend the same restaurant more than once
- The primary must be within the strict tradeoff. Backups may exceed this but should explain the tradeoff in their reason. 
    Example scenario: Restaurant A is the correct cuisine but 500m farther than the agreed distance or Restaurant B is within distance, 
    but it is the the second or third highest rated cuisine instead of first
- Prefer open, highly rated, highly reviewed places
- Return ONLY valid JSON, no explanation, no markdown backticks"""

    user_prompt = f"""Group preferences:
{preferences_text}

Restaurants:
{restaurants_text}

Strict radius:
{strict_radius}

Return this exact JSON structure:
{{
  "personality_lines": {{"name": "one sentence ≤10 words\\noptional second sentence ≤10 words"}},
  "agreements": "sentence one ≤10 words\\nsentence two ≤10 words",
  "conflicts": "sentence one ≤10 words\\nsentence two ≤10 words",
  "primary": {{"name": "...", "reason": "...", "maps_link": "..."}},
  "backups": [{{"name": "...", "reason": "...", "maps_link": "..."}}]
}}"""

    try:
        raw = call_gemini(system_prompt, user_prompt)
    except (ClientError, ServerError) as e:
        if _gemini_is_rate_limited(e) and config.GROQ_API_KEY:
            config.logger.warning(f"Gemini rate limited ({e.code}), falling back to Groq")
            raw = call_groq(system_prompt, user_prompt)
        else:
            config.logger.exception(f"Gemini call failed code={e.code}")

            # 429 = rate limited, 503 = temporarily overloaded
            if e.code in (429, 503):
                raise errors.UpstreamUnavailable(f"gemini status={e.code}") from e
            raise errors.UpstreamBadResponse(f"gemini status={e.code}") from e
    reveal = parse_reveal_response(raw)
    reveal = photos.enrich_reveal_photos(reveal, restaurants)
    return reveal
