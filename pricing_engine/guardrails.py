"""
Business rules that constrain candidate prices regardless of what the
demand model predicts. Per PIA_AI_Pricing_System_Roadmap.md, Phase 4.4.
"""
PRICE_FLOOR_MULTIPLIER = 0.7
PRICE_CEILING_MULTIPLIER = 2.5
COMPETITOR_CEILING_MARGIN = 0.15
COMPETITOR_CEILING_CAPACITY_EXCEPTION = 0.85
URGENCY_DAYS_THRESHOLD = 3
URGENCY_CAPACITY_THRESHOLD = 0.30

def get_price_bounds(base_fare: float) -> tuple[float, float]:
    floor = base_fare * PRICE_FLOOR_MULTIPLIER
    ceiling = base_fare * PRICE_CEILING_MULTIPLIER
    return floor, ceiling

def apply_competitor_ceiling(candidate_price, competitor_avg_price, capacity_used_ratio):
    if competitor_avg_price is None:
        return candidate_price
    if capacity_used_ratio > COMPETITOR_CEILING_CAPACITY_EXCEPTION:
        return candidate_price
    max_allowed = competitor_avg_price * (1 + COMPETITOR_CEILING_MARGIN)
    return min(candidate_price, max_allowed)

def apply_urgency_modifier(candidate_price, days_to_departure, remaining_seats_ratio, boost_factor=1.10):
    if days_to_departure < URGENCY_DAYS_THRESHOLD and remaining_seats_ratio > URGENCY_CAPACITY_THRESHOLD:
        return candidate_price * boost_factor
    return candidate_price

def apply_all_guardrails(candidate_price, base_fare, competitor_avg_price, days_to_departure, remaining_seats_ratio):
    floor, ceiling = get_price_bounds(base_fare)
    price = min(max(candidate_price, floor), ceiling)
    capacity_used_ratio = 1 - remaining_seats_ratio
    price = apply_competitor_ceiling(price, competitor_avg_price, capacity_used_ratio)
    price = apply_urgency_modifier(price, days_to_departure, remaining_seats_ratio)
    price = min(max(price, floor), ceiling)
    return price
