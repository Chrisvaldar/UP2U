TRAVEL_LIMITS = {
    "short walk (<500m)": 500,
    "public transport (<2km)": 2000,
    "don't mind": 3000,
}
DEFAULT_TRAVEL_LIMIT = 500  # conservative fallback if answer missing


def get_search_radius(users: list[dict]) -> float:
    """How far the group is willing to travel — limited by the strictest person."""
    limits = [
        TRAVEL_LIMITS.get(u.get("travel_distance", ""), DEFAULT_TRAVEL_LIMIT)
        for u in users
    ]
    return min(limits) if limits else DEFAULT_TRAVEL_LIMIT


def rank_restaurants_for_group(
    restaurants: list[dict], radius: float, users: list[dict]
):
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
    lower_res = [str.lower(s) for s in restaurant["cuisines"]]
    lower_ranked = [str.lower(s) for s in ranked_cuisines]
    for res in lower_ranked:
        if any(res in rc for rc in lower_res):
            return True
    return False


def score_cuisine(restaurant: dict, ranked_cuisines: list[str]) -> int:
    res_cuisines = [str.lower(s) for s in restaurant["cuisines"]]
    ranked_cuisines = [str.lower(s) for s in ranked_cuisines]
    best_match = 0
    points = [10, 7, 5, 3]
    for index, cuisine in enumerate(ranked_cuisines):
        if any(cuisine in rc for rc in res_cuisines):
            best_match = max(best_match, points[min(index, len(points) - 1)])
    return best_match


def score_restaurant_for_person(restaurant: dict, user: dict, radius: float) -> float:
    total = score_cuisine(restaurant, user["cuisines_ranked"])

    if radius > 0:
        total += (radius - restaurant["distance_meters"]) / radius * 5
    total += restaurant["rating"] * 0.5

    return total


def score_restaurant_for_group(
    restaurant: dict, users: list[dict], radius: float
) -> float:
    return min(score_restaurant_for_person(restaurant, user, radius) for user in users)
