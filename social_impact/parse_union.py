"""Union membership rates by major occupation group.

Source: BLS 2024 union membership report
https://www.bls.gov/news.release/union2.t03.htm
Data is at 2-digit SOC major group level only.
"""

# Hardcoded values from BLS 2024 union membership report
# Major occupation group -> union membership rate (%)
UNION_RATES_2024 = {
    "11": 5.1,   # Management
    "13": 4.3,   # Business and financial operations
    "15": 5.2,   # Computer and mathematical
    "17": 8.3,   # Architecture and engineering
    "19": 10.5,  # Life, physical, and social science
    "21": 15.4,  # Community and social service
    "23": 5.8,   # Legal
    "25": 33.8,  # Educational instruction and library
    "27": 8.0,   # Arts, design, entertainment, sports, media
    "29": 11.6,  # Healthcare practitioners and technical
    "31": 10.8,  # Healthcare support
    "33": 33.9,  # Protective service
    "35": 4.7,   # Food preparation and serving
    "37": 11.9,  # Building and grounds cleaning
    "39": 5.7,   # Personal care and service
    "41": 3.4,   # Sales and related
    "43": 8.1,   # Office and administrative support
    "45": 3.2,   # Farming, fishing, forestry
    "47": 12.4,  # Construction and extraction
    "49": 10.8,  # Installation, maintenance, repair
    "51": 8.7,   # Production
    "53": 14.6,  # Transportation and material moving
}


def get_union_rate(soc_code):
    """Get union rate for a SOC code using its 2-digit major group."""
    major = soc_code.split("-")[0]
    return UNION_RATES_2024.get(major)
