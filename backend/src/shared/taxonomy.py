CORE_CATEGORIES = frozenset([
    "Fruits & Vegetables", 
    "Dairy & Bakery", 
    "Snacks & Beverages", 
    "Staples/Grocery", 
    "Personal Care & Cleaning"
])

EXPLORATORY_CATEGORIES = frozenset([
    "Electronics & Accessories", 
    "Beauty & Skincare", 
    "Pharmacy/Health", 
    "Baby Care", 
    "Pet Care", 
    "Stationery & Print", 
    "Home & Kitchen", 
    "Books"
])

def classify_category_tier(category: str) -> str:
    """Returns 'core', 'exploratory', or 'unknown' for a given canonical category."""
    if category in CORE_CATEGORIES:
        return "core"
    if category in EXPLORATORY_CATEGORIES:
        return "exploratory"
    return "unknown"
