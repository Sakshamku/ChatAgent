"""
LangChain Tools for Coding Profile Analytics.

These tools are registered with the LangGraph agent so the AI
can automatically fetch and analyze coding profiles when users
ask coding-related questions.
"""

from __future__ import annotations

import json
from typing import Optional

from langchain_core.tools import tool

from backend.coding_platforms.leetcode import (
    fetch_leetcode_profile, fetch_leetcode_topics, fetch_leetcode_contests
)
from backend.coding_platforms.gfg import fetch_gfg_profile
from backend.coding_platforms.analytics import (
    analyze_topics, get_weakest_topic, get_strongest_topic,
    generate_dsa_roadmap, estimate_faang_readiness,
    get_interview_readiness_score, get_daily_recommendations
)
from backend.coding_platforms.charts import (
    create_topic_distribution_chart, create_difficulty_bar_chart,
    create_contest_rating_chart, create_progress_trend_chart,
    create_faang_radar_chart
)
from backend.database import (
    save_coding_profile, get_coding_profiles, delete_coding_profile,
    save_coding_stats, get_latest_coding_stats,
    save_topic_stats, get_topic_stats,
    save_contest_history, get_contest_history,
)


# =========================================================
# Helper
# =========================================================

def _get_user_id(thread_id: Optional[str]) -> str:
    """Use thread_id as user_id for profile isolation."""
    return thread_id or "default_user"


# =========================================================
# LeetCode Tools
# =========================================================

@tool
def get_leetcode_stats(username: str, thread_id: Optional[str] = None):
    """
    Fetch and analyze a LeetCode user profile.
    
    Use this when the user asks about their LeetCode stats, solved problems,
    difficulty breakdown, ranking, or streak.
    
    Args:
        username: LeetCode username
        thread_id: Thread ID for profile storage
    """
    user_id = _get_user_id(thread_id)
    
    # Fetch profile
    profile = fetch_leetcode_profile(username)
    
    if "error" in profile:
        return {"error": profile["error"]}
    
    # Save to database
    save_coding_profile(user_id, "leetcode", username)
    save_coding_stats(user_id, "leetcode", profile)
    
    # Fetch and save topics
    topics = fetch_leetcode_topics(username)
    if topics:
        save_topic_stats(user_id, "leetcode", topics)
    
    # Fetch and save contests
    contests = fetch_leetcode_contests(username)
    if contests:
        save_contest_history(user_id, "leetcode", contests)
    
    # Extract current contest rating
    contest_rating = 0
    if contests and len(contests) > 0:
        current = contests[0]
        contest_rating = current.get("current_rating", 0)
    
    profile["contest_rating"] = contest_rating
    
    return {
        "platform": "leetcode",
        "username": username,
        "total_solved": profile.get("total_solved", 0),
        "easy_count": profile.get("easy_count", 0),
        "medium_count": profile.get("medium_count", 0),
        "hard_count": profile.get("hard_count", 0),
        "ranking": profile.get("ranking", 0),
        "contest_rating": contest_rating,
        "streak": profile.get("streak", 0),
        "topics_count": len(topics),
        "contests_count": len(contests) - 1 if contests else 0,
    }


@tool
def get_gfg_stats(username: str, thread_id: Optional[str] = None):
    """
    Fetch and analyze a GeeksforGeeks user profile.
    
    Use this when the user asks about their GFG stats, coding score,
    institution rank, or solved problems on GFG.
    
    Args:
        username: GeeksforGeeks username
        thread_id: Thread ID for profile storage
    """
    user_id = _get_user_id(thread_id)
    
    profile = fetch_gfg_profile(username)
    
    if "error" in profile:
        return {"error": profile["error"]}
    
    # Save to database
    save_coding_profile(user_id, "gfg", username)
    save_coding_stats(user_id, "gfg", profile)
    
    return {
        "platform": "gfg",
        "username": username,
        "coding_score": profile.get("coding_score", 0),
        "total_problems_solved": profile.get("total_problems_solved", 0),
        "monthly_score": profile.get("monthly_score", 0),
        "institute_rank": profile.get("institute_rank", 0),
        "country_rank": profile.get("country_rank", 0),
        "overall_rank": profile.get("overall_rank", 0),
        "streak": profile.get("streak", 0),
    }


# =========================================================
# Analytics Tools
# =========================================================

@tool
def analyze_coding_topics(platform: str = "leetcode", thread_id: Optional[str] = None):
    """
    Analyze topic-wise solved problem counts for the connected coding profile.
    
    Use this when the user asks about topic analysis, which topics they've
    practiced, or wants a breakdown of their skills by topic.
    
    Args:
        platform: Platform to analyze ("leetcode" or "gfg")
        thread_id: Thread ID for profile lookup
    """
    user_id = _get_user_id(thread_id)
    
    # Try to get from database first
    topics = get_topic_stats(user_id, platform)
    
    if not topics:
        # Try to fetch from connected profile
        profiles = get_coding_profiles(user_id)
        platform_profile = [p for p in profiles if p["platform"] == platform]
        
        if platform_profile:
            username = platform_profile[0]["username"]
            if platform == "leetcode":
                topics = fetch_leetcode_topics(username)
                if topics:
                    save_topic_stats(user_id, platform, topics)
            else:
                return {"error": "Topic analysis not available for GFG yet"}
        else:
            return {"error": f"No {platform} profile connected. Use get_leetcode_stats or get_gfg_stats first."}
    
    analysis = analyze_topics(topics)
    
    # Generate chart data
    chart = create_topic_distribution_chart(topics)
    
    return {
        "analysis": analysis,
        "chart": chart,
        "topics": topics[:15],  # Top 15 topics
    }


@tool
def weakest_topic_analysis(platform: str = "leetcode", thread_id: Optional[str] = None):
    """
    Find the weakest topic and provide improvement suggestions.
    
    Use this when the user asks about their weakest area, what to improve,
    or where they should focus their practice.
    
    Args:
        platform: Platform to analyze
        thread_id: Thread ID for profile lookup
    """
    user_id = _get_user_id(thread_id)
    topics = get_topic_stats(user_id, platform)
    
    if not topics:
        return {"error": f"No topic data available. Connect your {platform} profile first."}
    
    result = get_weakest_topic(topics)
    return result


@tool
def strongest_topic_analysis(platform: str = "leetcode", thread_id: Optional[str] = None):
    """
    Find the strongest topic based on solved count and weight.
    
    Use this when the user asks about their strongest area or best topic.
    
    Args:
        platform: Platform to analyze
        thread_id: Thread ID for profile lookup
    """
    user_id = _get_user_id(thread_id)
    topics = get_topic_stats(user_id, platform)
    
    if not topics:
        return {"error": f"No topic data available. Connect your {platform} profile first."}
    
    result = get_strongest_topic(topics)
    return result


@tool
def generate_coding_roadmap(
    target_days: int = 60,
    target_company: str = "general",
    platform: str = "leetcode",
    thread_id: Optional[str] = None,
):
    """
    Generate a personalized DSA roadmap based on the user's current stats.
    
    Use this when the user asks for a study plan, preparation roadmap,
    or wants to know what to study next.
    
    Args:
        target_days: Number of days for the roadmap (default 60)
        target_company: Target company for preparation (e.g., "amazon", "google", "meta")
        platform: Platform to use for analysis
        thread_id: Thread ID for profile lookup
    """
    user_id = _get_user_id(thread_id)
    
    topics = get_topic_stats(user_id, platform)
    stats = get_latest_coding_stats(user_id, platform)
    
    if not topics and not stats:
        return {"error": f"No data available. Connect your {platform} profile first."}
    
    profile = dict(stats) if stats else {}
    roadmap = generate_dsa_roadmap(topics, profile, target_days, target_company)
    
    # Generate progress chart
    chart = create_progress_trend_chart(topics)
    roadmap["chart"] = chart
    
    return roadmap


@tool
def contest_analysis(platform: str = "leetcode", thread_id: Optional[str] = None):
    """
    Analyze contest performance and rating trends.
    
    Use this when the user asks about their contest performance,
    rating history, or contest consistency.
    
    Args:
        platform: Platform to analyze
        thread_id: Thread ID for profile lookup
    """
    user_id = _get_user_id(thread_id)
    contests = get_contest_history(user_id, platform)
    
    if not contests:
        return {"error": f"No contest data available. Connect your {platform} profile first."}
    
    # Generate rating chart
    chart = create_contest_rating_chart(contests)
    
    # Analyze trend
    ratings = [c.get("rating", 0) for c in contests if c.get("rating", 0) > 0]
    
    trend = "stable"
    if len(ratings) >= 3:
        recent_avg = sum(ratings[:3]) / 3
        older_avg = sum(ratings[-3:]) / 3 if len(ratings) >= 6 else recent_avg
        if recent_avg > older_avg * 1.05:
            trend = "improving"
        elif recent_avg < older_avg * 0.95:
            trend = "declining"
    
    return {
        "total_contests": len(contests),
        "latest_rating": ratings[0] if ratings else 0,
        "highest_rating": max(ratings) if ratings else 0,
        "lowest_rating": min(ratings) if ratings else 0,
        "trend": trend,
        "chart": chart,
        "recent_contests": contests[:5],
    }


@tool
def coding_progress_summary(platform: str = "leetcode", thread_id: Optional[str] = None):
    """
    Get a comprehensive coding progress summary with FAANG readiness,
    interview readiness, and daily recommendations.
    
    Use this when the user asks for an overall analysis, progress check,
    or wants to know how they're doing overall.
    
    Args:
        platform: Platform to analyze
        thread_id: Thread ID for profile lookup
    """
    user_id = _get_user_id(thread_id)
    
    stats = get_latest_coding_stats(user_id, platform)
    topics = get_topic_stats(user_id, platform)
    
    if not stats and not topics:
        return {"error": f"No data available. Connect your {platform} profile first."}
    
    profile = dict(stats) if stats else {}
    
    # FAANG readiness
    faang = estimate_faang_readiness(profile, topics)
    
    # Interview readiness
    interview = get_interview_readiness_score(profile, topics)
    
    # Daily recommendations
    daily = get_daily_recommendations(topics, profile)
    
    # Charts
    difficulty_chart = create_difficulty_bar_chart(profile)
    faang_radar = create_faang_radar_chart(faang)
    
    return {
        "profile_summary": {
            "total_solved": profile.get("total_solved", 0),
            "easy": profile.get("easy_count", 0),
            "medium": profile.get("medium_count", 0),
            "hard": profile.get("hard_count", 0),
            "ranking": profile.get("ranking", 0),
            "streak": profile.get("streak", 0),
        },
        "faang_readiness": faang,
        "interview_readiness": interview,
        "daily_recommendations": daily,
        "charts": {
            "difficulty": difficulty_chart,
            "faang_radar": faang_radar,
        },
    }


@tool
def list_connected_profiles(thread_id: Optional[str] = None):
    """
    List all connected coding profiles for the current user.
    
    Use this to check which platforms are connected before
    running analytics.
    
    Args:
        thread_id: Thread ID for profile lookup
    """
    user_id = _get_user_id(thread_id)
    profiles = get_coding_profiles(user_id)
    
    if not profiles:
        return {"profiles": [], "message": "No coding profiles connected yet. Use get_leetcode_stats or get_gfg_stats to connect."}
    
    return {
        "profiles": [{"platform": p["platform"], "username": p["username"]} for p in profiles],
        "message": f"{len(profiles)} profile(s) connected"
    }
