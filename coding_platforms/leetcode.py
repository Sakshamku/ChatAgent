"""
LeetCode Integration via GraphQL API.

Fetches profile stats, topic-wise breakdown, contest history,
submission stats, and streak data.
"""

from __future__ import annotations

import json
import time
import functools
from typing import Any, Dict, List, Optional

import requests

# =========================================================
# Configuration
# =========================================================

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
LEETCODE_API_URL = "https://leetcode.com/api"
CACHE_TTL = 3600  # 1 hour cache

# =========================================================
# In-memory cache
# =========================================================

_profile_cache: Dict[str, dict] = {}
_topics_cache: Dict[str, list] = {}
_contests_cache: Dict[str, list] = {}

def _is_cache_valid(cache_key: str, cache_store: dict) -> bool:
    """Check if cached data is still valid."""
    if cache_key not in cache_store:
        return False
    entry = cache_store[cache_key]
    if not isinstance(entry, dict):
        return False
    return (time.time() - entry.get("_timestamp", 0)) < CACHE_TTL


def _get_cached(cache_key: str, cache_store: dict) -> Any:
    """Return cached payload without metadata fields."""
    entry = cache_store[cache_key]
    if isinstance(entry, dict) and "_data" in entry:
        return entry["_data"]
    if isinstance(entry, dict):
        return {k: v for k, v in entry.items() if k != "_timestamp"}
    return entry


def _set_cache(cache_key: str, data: Any, cache_store: dict) -> Any:
    """Store data in cache with timestamp."""
    if isinstance(data, dict):
        cache_store[cache_key] = {**data, "_timestamp": time.time()}
    else:
        cache_store[cache_key] = {"_data": data, "_timestamp": time.time()}
    return data


# =========================================================
# GraphQL Queries
# =========================================================

PROFILE_QUERY = """
query userProfile($username: String!) {
    matchedUser(username: $username) {
        username
        submitStatsGlobal {
            acSubmissionNum {
                difficulty
                count
            }
        }
        profile {
            ranking
            reputation
            starRating
        }
        submitStats {
            totalSubmissionNum {
                difficulty
                count
                submissions
            }
            acSubmissionNum {
                difficulty
                count
                submissions
            }
        }
    }
}
"""

TOPICS_QUERY = """
query skillStats($username: String!) {
    matchedUser(username: $username) {
        tagProblemCounts {
            fundamental {
                tagName
                tagSlug
                problemsSolved
            }
            intermediate {
                tagName
                tagSlug
                problemsSolved
            }
            advanced {
                tagName
                tagSlug
                problemsSolved
            }
        }
    }
}
"""

CONTEST_QUERY = """
query userContestRanking($username: String!) {
    userContestRanking(username: $username) {
        attendedContestsCount
        rating
        globalRanking
        topPercentage
    }
    userContestRankingHistory(username: $username) {
        contest {
            title
            startTime
        }
        rating
        ranking
    }
}
"""

CALENDAR_QUERY = """
query userProfileCalendar($username: String!, $year: Int) {
    matchedUser(username: $username) {
        userCalendar(year: $year) {
            streak
            totalActiveDays
        }
    }
}
"""

# =========================================================
# API Functions
# =========================================================

def _graphql_request(query: str, variables: dict) -> Optional[dict]:
    """Make a GraphQL request to LeetCode API."""
    try:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        payload = {"query": query, "variables": variables}
        response = requests.post(
            LEETCODE_GRAPHQL_URL,
            json=payload,
            headers=headers,
            timeout=15,
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"LeetCode API error: {e}")
        return None


def fetch_leetcode_profile(username: str) -> Dict[str, Any]:
    """
    Fetch LeetCode user profile with solved problems, difficulty breakdown,
    ranking, and submission stats.
    
    Args:
        username: LeetCode username
        
    Returns:
        Dict with profile data or error
    """
    cache_key = f"profile_{username}"
    if _is_cache_valid(cache_key, _profile_cache):
        return _get_cached(cache_key, _profile_cache)
    
    data = _graphql_request(PROFILE_QUERY, {"username": username})
    
    if not data or not data.get("data", {}).get("matchedUser"):
        # Check for GraphQL errors
        if data and data.get("errors"):
            err_msg = data["errors"][0].get("message", "Unknown error")
            return {"error": f"LeetCode API error: {err_msg}"}
        return {"error": f"LeetCode user '{username}' not found or API error"}
    
    user = data["data"]["matchedUser"]
    
    # Parse submission stats — try submitStatsGlobal first, then submitStats
    ac_stats = user.get("submitStatsGlobal", {}).get("acSubmissionNum", [])
    if not ac_stats:
        ac_stats = user.get("submitStats", {}).get("acSubmissionNum", [])
    
    easy_count = medium_count = hard_count = total_count = 0
    for stat in ac_stats:
        diff = stat.get("difficulty", "").lower()
        count = stat.get("count", 0)
        if diff == "easy":
            easy_count = count
        elif diff == "medium":
            medium_count = count
        elif diff == "hard":
            hard_count = count
        elif diff == "all":
            total_count = count
    
    # Parse ranking
    ranking = user.get("profile", {}).get("ranking", 0) or 0
    
    # Fetch streak info
    streak = 0
    active_days = 0
    import datetime
    current_year = datetime.datetime.now().year
    cal_data = _graphql_request(CALENDAR_QUERY, {"username": username, "year": current_year})
    if cal_data and cal_data.get("data", {}).get("matchedUser", {}).get("userCalendar"):
        cal = cal_data["data"]["matchedUser"]["userCalendar"]
        streak = cal.get("streak", 0)
        active_days = cal.get("totalActiveDays", 0)
    
    result = {
        "platform": "leetcode",
        "username": username,
        "total_solved": total_count,
        "easy_count": easy_count,
        "medium_count": medium_count,
        "hard_count": hard_count,
        "ranking": ranking,
        "streak": streak,
        "active_days": active_days,
    }
    
    _set_cache(cache_key, result, _profile_cache)
    return result


def fetch_leetcode_topics(username: str) -> List[Dict[str, Any]]:
    """
    Fetch topic-wise solved problem counts from LeetCode.
    
    Args:
        username: LeetCode username
        
    Returns:
        List of dicts with topic_name and solved_count
    """
    cache_key = f"topics_{username}"
    if _is_cache_valid(cache_key, _topics_cache):
        return _get_cached(cache_key, _topics_cache)
    
    data = _graphql_request(TOPICS_QUERY, {"username": username})
    
    if not data or not data.get("data", {}).get("matchedUser"):
        return []
    
    tag_data = data["data"]["matchedUser"].get("tagProblemCounts", {})
    
    topics = []
    # Flatten all categories: fundamental, intermediate, advanced
    for category in ["fundamental", "intermediate", "advanced"]:
        category_list = tag_data.get(category, [])
        for tag in category_list:
            topics.append({
                "topic_name": tag.get("tagName", ""),
                "solved_count": tag.get("problemsSolved", 0),
            })
    
    # Sort by solved count descending
    topics.sort(key=lambda x: x["solved_count"], reverse=True)
    
    _set_cache(cache_key, topics, _topics_cache)
    return topics


def fetch_leetcode_contests(username: str) -> List[Dict[str, Any]]:
    """
    Fetch contest history from LeetCode.
    
    Args:
        username: LeetCode username
        
    Returns:
        List of contest results with rating, ranking, date
    """
    cache_key = f"contests_{username}"
    if _is_cache_valid(cache_key, _contests_cache):
        return _get_cached(cache_key, _contests_cache)
    
    data = _graphql_request(CONTEST_QUERY, {"username": username})
    
    if not data or not data.get("data"):
        if data and data.get("errors"):
            # Contest data may not be available for all users
            return []
        return []
    
    data = data["data"]
    
    contests = []
    
    # Current contest stats
    current = data.get("userContestRanking")
    current_stats = {}
    if current:
        current_stats = {
            "attended": current.get("attendedContestsCount", 0),
            "current_rating": current.get("rating", 0),
            "global_ranking": current.get("globalRanking", 0),
            "top_percentage": current.get("topPercentage", 0),
        }
    
    # Contest history
    history = data.get("userContestRankingHistory", [])
    for entry in history:
        contest = entry.get("contest", {})
        import datetime
        timestamp = contest.get("startTime", 0)
        contest_date = datetime.datetime.fromtimestamp(timestamp).isoformat() if timestamp else ""
        
        contests.append({
            "contest_name": contest.get("title", ""),
            "rating": entry.get("rating", 0),
            "ranking": entry.get("ranking", 0),
            "contest_date": contest_date,
        })
    
    # Sort by date descending
    contests.sort(key=lambda x: x.get("contest_date", ""), reverse=True)
    
    # Add current stats as metadata
    contests.insert(0, {**current_stats, "contest_name": "__current_stats__"})
    
    _set_cache(cache_key, contests, _contests_cache)
    return contests
