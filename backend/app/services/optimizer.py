import math

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def optimize_route(places: list[dict]) -> list[dict]:
    """Sorts places using a Traveling Salesperson Nearest-Neighbor algorithm.
    Starts with the most popular place based on ratings & reviews count."""
    if not places:
        return []

    # 1. Calculate popularity score for each place
    # score = rating * ln(reviews_count + 2)  [to avoid ln(0) or ln(1)=0]
    scored_places = []
    for p in places:
        rating = p.get("rating") or 4.0
        reviews = p.get("reviews_count") or 0
        score = rating * math.log(reviews + 2)
        scored_places.append((score, p))

    # Sort descending by score
    scored_places.sort(key=lambda x: x[0], reverse=True)
    
    # Extract places back
    candidates = [sp[1] for sp in scored_places]
    
    # 2. Nearest Neighbor Traversal
    optimized = []
    current = candidates.pop(0) # Start with the most popular attraction
    optimized.append(current)
    
    while candidates:
        nearest_idx = 0
        min_dist = float('inf')
        for idx, cand in enumerate(candidates):
            dist = haversine_distance(
                current["lat"], current["lng"],
                cand["lat"], cand["lng"]
            )
            if dist < min_dist:
                min_dist = dist
                nearest_idx = idx
                
        # Move to nearest
        current = candidates.pop(nearest_idx)
        optimized.append(current)
        
    return optimized
