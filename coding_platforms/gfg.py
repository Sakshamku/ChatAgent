"""
GeeksforGeeks Integration via Profile Scraping.

Fetches coding score, institution rank, solved problems,
and profile stats from GFG public profiles.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

import requests

# =========================================================
# Configuration
# =========================================================

GFG_PROFILE_URL = "https://auth.geeksforgeeks.org/user/{username}/profile"
GFG_API_URL = "https://practiceapi.geeksforgeeks.org/api/v1/user/{username}/profile"
CACHE_TTL = 3600  # 1 hour

# =========================================================
# In-memory cache
# =========================================================

_profile_cache: Dict[str, dict] = {}
_stats_cache: Dict[str, dict] = {}


def _is_cache_valid(cache_key: str, cache_store: dict) -> bool:
    if cache_key not in cache_store:
        return False
    entry = cache_store[cache_key]
    return (time.time() - entry.get("_timestamp", 0)) < CACHE_TTL


# =========================================================
# API Functions
# =========================================================

def fetch_gfg_profile(username: str) -> Dict[str, Any]:
    """
    Fetch GFG user profile using the practice API.
    
    Args:
        username: GeeksforGeeks username
        
    Returns:
        Dict with profile data or error
    """
    cache_key = f"profile_{username}"
    if _is_cache_valid(cache_key, _profile_cache):
        cached = _profile_cache[cache_key]
        return {k: v for k, v in cached.items() if k != "_timestamp"}
    
    # Try the practice API first
    try:
        api_url = GFG_API_URL.format(username=username)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        response = requests.get(api_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("result"):
                result = data["result"]
                
                profile_data = {
                    "platform": "gfg",
                    "username": username,
                    "name": result.get("name", ""),
                    "coding_score": result.get("coding_score", 0),
                    "total_problems_solved": result.get("total_problems_solved", 0),
                    "monthly_score": result.get("monthly_score", 0),
                    "institute_rank": result.get("institute_rank", 0),
                    "country_rank": result.get("country_rank", 0),
                    "overall_rank": result.get("overall_rank", 0),
                    "streak": result.get("streak", 0),
                    "language_proficiency": result.get("language_proficiency", {}),
                    "college": result.get("college", ""),
                    "profile_image": result.get("profile_image", ""),
                }
                
                _profile_cache[cache_key] = {**profile_data, "_timestamp": time.time()}
                return profile_data
    except Exception as e:
        print(f"GFG API error: {e}")
    
    # Fallback: scrape the profile page
    return scrape_gfg_stats(username)


def scrape_gfg_stats(username: str) -> Dict[str, Any]:
    """
    Scrape GFG profile page as fallback when API is unavailable.
    
    Args:
        username: GeeksforGeeks username
        
    Returns:
        Dict with scraped stats or error
    """
    cache_key = f"scrape_{username}"
    if _is_cache_valid(cache_key, _stats_cache):
        cached = _stats_cache[cache_key]
        return {k: v for k, v in cached.items() if k != "_timestamp"}
    
    try:
        profile_url = GFG_PROFILE_URL.format(username=username)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        response = requests.get(profile_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return {"error": f"GFG user '{username}' not found or page unavailable"}
        
        html = response.text
        
        # Try to extract stats from the HTML
        # GFG embeds profile data in script tags or specific div elements
        result = {
            "platform": "gfg",
            "username": username,
            "coding_score": _extract_number(html, r"coding_score[\":\s]+(\d+)"),
            "total_problems_solved": _extract_number(html, r"problems_solved[\":\s]+(\d+)") or 
                                     _extract_number(html, r"(\d+)\s*(?:Problems?|Solved)"),
            "monthly_score": _extract_number(html, r"monthly_score[\":\s]+(\d+)"),
            "institute_rank": _extract_number(html, r"institute_rank[\":\s]+(\d+)") or
                              _extract_number(html, r"Rank[:\s]*(\d+)"),
        }
        
        # Try to find JSON data embedded in the page
        json_match = re.search(r'window\.profileData\s*=\s*({.*?});', html, re.DOTALL)
        if json_match:
            try:
                import json
                profile_json = json.loads(json_match.group(1))
                result.update({
                    "coding_score": profile_json.get("coding_score", result.get("coding_score", 0)),
                    "total_problems_solved": profile_json.get("total_problems_solved", result.get("total_problems_solved", 0)),
                    "monthly_score": profile_json.get("monthly_score", result.get("monthly_score", 0)),
                })
            except (json.JSONDecodeError, AttributeError):
                pass
        
        _stats_cache[cache_key] = {**result, "_timestamp": time.time()}
        return result
        
    except Exception as e:
        return {"error": f"Failed to fetch GFG profile for '{username}': {e}"}


def _extract_number(html: str, pattern: str) -> int:
    """Extract a number from HTML using regex pattern."""
    match = re.search(pattern, html, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except (ValueError, IndexError):
            return 0
    return 0
