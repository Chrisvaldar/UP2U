TRAVEL_LIMITS = {
    "short walk (<500m)": 500,
    "public transport (<2km)": 2000,
    "don't mind": 3000,
}
DEFAULT_TRAVEL_LIMIT = 500  # conservative fallback if answer missing


def get_search_radius(users: list[dict]) -> float:
    """
    Determine how far the group is willing to travel.

    Args:
        users: Participant answer dicts, each with an optional travel_distance key.

    Returns:
        The minimum travel limit in metres across the group, mapped from
        TRAVEL_LIMITS, or DEFAULT_TRAVEL_LIMIT when no users are provided.
    """
    limits = [
        TRAVEL_LIMITS.get(u.get("travel_distance", ""), DEFAULT_TRAVEL_LIMIT)
        for u in users
    ]
    return min(limits) if limits else DEFAULT_TRAVEL_LIMIT


def rank_restaurants_for_group(
    restaurants: list[dict], radius: float, users: list[dict]
):
    """
    Filter and score restaurants for a group, then sort by group score.

    Args:
        restaurants: Cleaned restaurant dicts from places.get_nearby_restaurants.
        radius: Maximum travel distance in metres for scoring.
        users: Participant answer dicts with cuisines_ranked preferences.

    Returns:
        Restaurants sorted by _group_score descending. Prefers places that match
        every participant's ranked cuisines; falls back to all open restaurants
        if fewer than three matches are found.
    """
    open_and_distance = [r for r in restaurants if r["open_now"] != False]

    filtered = [
        r
        for r in open_and_distance
        if all(cuisine_matches(r, u["cuisines_ranked"]) for u in users)
    ]
    if len(filtered) < 3:
        filtered = open_and_distance

    for r in filtered:
        r["_group_score"] = score_restaurant_for_group(r, users, radius)

    return sorted(filtered, key=lambda r: r["_group_score"], reverse=True)


def cuisine_matches(restaurant, ranked_cuisines):
    """
    Check whether any ranked cuisine appears in the restaurant's cuisine tags.

    Args:
        restaurant: Restaurant dict with a cuisines list.
        ranked_cuisines: Ordered list of cuisine preferences for one participant.

    Returns:
        True if any ranked cuisine is a substring of a restaurant cuisine tag.
    """
    lower_res = [str.lower(s) for s in restaurant["cuisines"]]
    lower_ranked = [str.lower(s) for s in ranked_cuisines]
    for res in lower_ranked:
        if any(res in rc for rc in lower_res):
            return True
    return False


def score_cuisine(restaurant: dict, ranked_cuisines: list[str]) -> int:
    """
    Score how well a restaurant matches one participant's cuisine ranking.

    Args:
        restaurant: Restaurant dict with a cuisines list.
        ranked_cuisines: Ordered cuisine preferences for one participant.

    Returns:
        Points from the best matching rank: 10, 7, 5, or 3 by position.
    """
    res_cuisines = [str.lower(s) for s in restaurant["cuisines"]]
    ranked_cuisines = [str.lower(s) for s in ranked_cuisines]
    best_match = 0
    points = [10, 7, 5, 3]
    for index, cuisine in enumerate(ranked_cuisines):
        if any(cuisine in rc for rc in res_cuisines):
            best_match = max(best_match, points[min(index, len(points) - 1)])
    return best_match


def score_restaurant_for_person(restaurant: dict, user: dict, radius: float) -> float:
    """
    Compute a composite score for one participant at one restaurant.

    Args:
        restaurant: Restaurant dict with cuisines, distance_meters, and rating.
        user: Participant answer dict with cuisines_ranked preferences.
        radius: Maximum travel distance in metres used for proximity scoring.

    Returns:
        Cuisine score plus distance bonus (up to 5) and rating weight (rating * 0.5).
    """
    total = score_cuisine(restaurant, user["cuisines_ranked"])

    if radius > 0:
        total += (radius - restaurant["distance_meters"]) / radius * 5
    total += restaurant["rating"] * 0.5

    return total


def score_restaurant_for_group(
    restaurant: dict, users: list[dict], radius: float
) -> float:
    """
    Compute the group score as the minimum individual score across participants.

    Args:
        restaurant: Restaurant dict passed to score_restaurant_for_person.
        users: Participant answer dicts for each group member.
        radius: Maximum travel distance in metres for proximity scoring.

    Returns:
        The lowest score_restaurant_for_person result among all users.
    """
    return min(score_restaurant_for_person(restaurant, user, radius) for user in users)
