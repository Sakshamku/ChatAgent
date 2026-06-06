"""
AI-Powered Coding Analytics Engine.

Provides topic analysis, roadmap generation, FAANG readiness,
interview readiness scoring, and daily recommendations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


# =========================================================
# DSA Topic Taxonomy
# =========================================================

DSA_TOPICS = {
    "array": {"weight": 10, "category": "fundamental", "priority": "high"},
    "string": {"weight": 9, "category": "fundamental", "priority": "high"},
    "hash-table": {"weight": 8, "category": "fundamental", "priority": "high"},
    "math": {"weight": 7, "category": "fundamental", "priority": "medium"},
    "sorting": {"weight": 7, "category": "fundamental", "priority": "medium"},
    "two-pointers": {"weight": 8, "category": "technique", "priority": "high"},
    "sliding-window": {"weight": 7, "category": "technique", "priority": "high"},
    "binary-search": {"weight": 8, "category": "technique", "priority": "high"},
    "linked-list": {"weight": 7, "category": "data-structure", "priority": "medium"},
    "stack": {"weight": 7, "category": "data-structure", "priority": "medium"},
    "queue": {"weight": 6, "category": "data-structure", "priority": "medium"},
    "tree": {"weight": 9, "category": "data-structure", "priority": "high"},
    "binary-tree": {"weight": 9, "category": "data-structure", "priority": "high"},
    "bst": {"weight": 8, "category": "data-structure", "priority": "high"},
    "heap": {"weight": 7, "category": "data-structure", "priority": "medium"},
    "graph": {"weight": 10, "category": "advanced", "priority": "high"},
    "bfs": {"weight": 8, "category": "technique", "priority": "high"},
    "dfs": {"weight": 8, "category": "technique", "priority": "high"},
    "dynamic-programming": {"weight": 10, "category": "advanced", "priority": "high"},
    "greedy": {"weight": 8, "category": "technique", "priority": "high"},
    "backtracking": {"weight": 7, "category": "technique", "priority": "medium"},
    "divide-and-conquer": {"weight": 6, "category": "technique", "priority": "medium"},
    "recursion": {"weight": 7, "category": "technique", "priority": "medium"},
    "trie": {"weight": 6, "category": "data-structure", "priority": "medium"},
    "union-find": {"weight": 6, "category": "technique", "priority": "medium"},
    "topological-sort": {"weight": 5, "category": "technique", "priority": "medium"},
    "segment-tree": {"weight": 4, "category": "advanced", "priority": "low"},
    "bit-manipulation": {"weight": 5, "category": "technique", "priority": "low"},
    "matrix": {"weight": 6, "category": "fundamental", "priority": "medium"},
    "simulation": {"weight": 4, "category": "fundamental", "priority": "low"},
    "prefix-sum": {"weight": 6, "category": "technique", "priority": "medium"},
    "counting": {"weight": 5, "category": "technique", "priority": "low"},
    "memoization": {"weight": 7, "category": "technique", "priority": "medium"},
}

# FAANG topic requirements (minimum problems expected)
FAANG_TOPIC_MINIMUMS = {
    "array": 50, "string": 40, "hash-table": 30,
    "dynamic-programming": 40, "tree": 30, "graph": 25,
    "binary-search": 20, "two-pointers": 20,
    "sliding-window": 15, "linked-list": 15,
    "stack": 15, "bst": 15, "greedy": 20,
    "backtracking": 15, "bfs": 15, "dfs": 15,
    "heap": 10, "trie": 10,
}

# =========================================================
# Topic Analysis
# =========================================================

def analyze_topics(topics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze topic-wise solved counts and return comprehensive breakdown.
    
    Args:
        topics: List of {topic_name, solved_count} dicts
        
    Returns:
        Dict with analysis results
    """
    if not topics:
        return {"error": "No topic data available"}
    
    total_solved = sum(t["solved_count"] for t in topics)
    
    # Categorize topics
    fundamental = []
    technique = []
    data_structure = []
    advanced = []
    
    for topic in topics:
        name = topic["topic_name"].lower()
        count = topic["solved_count"]
        meta = DSA_TOPICS.get(name, {"weight": 5, "category": "fundamental", "priority": "low"})
        
        entry = {
            "topic": topic["topic_name"],
            "solved": count,
            "weight": meta["weight"],
            "priority": meta["priority"],
            "percentage": round(count / total_solved * 100, 1) if total_solved > 0 else 0,
        }
        
        cat = meta["category"]
        if cat == "fundamental":
            fundamental.append(entry)
        elif cat == "technique":
            technique.append(entry)
        elif cat == "data-structure":
            data_structure.append(entry)
        elif cat == "advanced":
            advanced.append(entry)
    
    return {
        "total_topics": len(topics),
        "total_solved": total_solved,
        "fundamental": sorted(fundamental, key=lambda x: x["solved"], reverse=True),
        "technique": sorted(technique, key=lambda x: x["solved"], reverse=True),
        "data_structure": sorted(data_structure, key=lambda x: x["solved"], reverse=True),
        "advanced": sorted(advanced, key=lambda x: x["solved"], reverse=True),
    }


def get_strongest_topic(topics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Find the strongest topic based on solved count and weight."""
    if not topics:
        return {"error": "No topic data available"}
    
    best = max(topics, key=lambda t: t["solved_count"] * DSA_TOPICS.get(t["topic_name"].lower(), {}).get("weight", 1))
    meta = DSA_TOPICS.get(best["topic_name"].lower(), {})
    
    return {
        "topic": best["topic_name"],
        "solved_count": best["solved_count"],
        "category": meta.get("category", "unknown"),
        "priority": meta.get("priority", "unknown"),
        "confidence_score": min(100, best["solved_count"] * 2),
    }


def get_weakest_topic(topics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Find the weakest topic that should be a priority."""
    if not topics:
        return {"error": "No topic data available"}
    
    # Filter to only high/medium priority topics (skip low-priority ones)
    priority_topics = [
        t for t in topics
        if DSA_TOPICS.get(t["topic_name"].lower(), {}).get("priority", "low") != "low"
    ]
    
    if not priority_topics:
        priority_topics = topics
    
    # Find the one with lowest solved count * weight ratio
    weakest = min(
        priority_topics,
        key=lambda t: t["solved_count"] / max(1, DSA_TOPICS.get(t["topic_name"].lower(), {}).get("weight", 1))
    )
    meta = DSA_TOPICS.get(weakest["topic_name"].lower(), {})
    
    # Improvement suggestions
    suggestions = _get_improvement_suggestions(weakest["topic_name"], weakest["solved_count"])
    
    return {
        "topic": weakest["topic_name"],
        "solved_count": weakest["solved_count"],
        "category": meta.get("category", "unknown"),
        "priority": meta.get("priority", "high"),
        "improvement_suggestions": suggestions,
        "recommended_problems": meta.get("weight", 5) * 3,
    }


def _get_improvement_suggestions(topic: str, current_count: int) -> List[str]:
    """Generate improvement suggestions for a weak topic."""
    suggestions = []
    meta = DSA_TOPICS.get(topic.lower(), {})
    
    if current_count == 0:
        suggestions.append(f"Start with basic {topic} problems (Easy difficulty)")
        suggestions.append(f"Study core concepts and patterns for {topic}")
        suggestions.append(f"Aim for at least 5 problems to build foundation")
    elif current_count < 10:
        suggestions.append(f"Practice more {topic} problems — aim for 10+ solved")
        suggestions.append(f"Focus on Medium difficulty {topic} problems")
        suggestions.append(f"Learn common patterns and templates for {topic}")
    elif current_count < 25:
        suggestions.append(f"Move to Hard {topic} problems for deeper understanding")
        suggestions.append(f"Time yourself on {topic} problems for speed improvement")
        suggestions.append(f"Review and optimize your {topic} solutions")
    else:
        suggestions.append(f"Good progress on {topic}! Focus on edge cases")
        suggestions.append(f"Practice contest-level {topic} problems")
    
    return suggestions


# =========================================================
# Roadmap Generation
# =========================================================

def generate_dsa_roadmap(
    topics: List[Dict[str, Any]],
    profile: Dict[str, Any],
    target_days: int = 60,
    target_company: str = "general",
) -> Dict[str, Any]:
    """
    Generate a personalized DSA roadmap based on current stats.
    
    Args:
        topics: Topic-wise solved counts
        profile: User profile data
        target_days: Number of days for roadmap
        target_company: Target company for preparation
        
    Returns:
        Dict with roadmap phases and daily plan
    """
    weak_topics = []
    moderate_topics = []
    strong_topics = []
    
    for topic in topics:
        name = topic["topic_name"].lower()
        count = topic["solved_count"]
        meta = DSA_TOPICS.get(name, {"weight": 5, "priority": "medium"})
        
        faang_min = FAANG_TOPIC_MINIMUMS.get(name, 10)
        ratio = count / faang_min if faang_min > 0 else 1
        
        if ratio < 0.4:
            weak_topics.append({**topic, "gap": faang_min - count, "priority": meta["priority"]})
        elif ratio < 0.8:
            moderate_topics.append({**topic, "gap": faang_min - count, "priority": meta["priority"]})
        else:
            strong_topics.append({**topic, "gap": max(0, faang_min - count), "priority": meta["priority"]})
    
    # Sort weak topics by priority and weight
    weak_topics.sort(key=lambda t: (t["priority"] == "high", t.get("gap", 0)), reverse=True)
    moderate_topics.sort(key=lambda t: (t["priority"] == "high",), reverse=True)
    
    # Build phases
    total_problems_gap = sum(t.get("gap", 0) for t in weak_topics + moderate_topics)
    daily_target = max(2, total_problems_gap // target_days) if total_problems_gap > 0 else 2
    
    # Phase allocation
    phase1_days = int(target_days * 0.4)  # Weak topics
    phase2_days = int(target_days * 0.35)  # Moderate topics
    phase3_days = target_days - phase1_days - phase2_days  # Revision + contests
    
    roadmap = {
        "target_days": target_days,
        "target_company": target_company,
        "daily_problem_target": daily_target,
        "total_problems_to_solve": total_problems_gap,
        "phases": [
            {
                "phase": 1,
                "name": "Foundation Building",
                "duration_days": phase1_days,
                "focus": "Weakest topics",
                "topics": [{"topic": t["topic_name"], "target_problems": t["gap"]} for t in weak_topics[:8]],
                "daily_plan": f"Solve {daily_target} problems from weak topics daily",
                "tips": [
                    "Start with Easy problems, graduate to Medium",
                    "Spend 30 min on concept review before solving",
                    "Write clean, well-commented solutions",
                ],
            },
            {
                "phase": 2,
                "name": "Skill Enhancement",
                "duration_days": phase2_days,
                "focus": "Moderate topics + Hard problems",
                "topics": [{"topic": t["topic_name"], "target_problems": t["gap"]} for t in moderate_topics[:6]],
                "daily_plan": f"Solve {daily_target} Medium/Hard problems + review weak areas",
                "tips": [
                    "Focus on Medium and Hard difficulty",
                    "Practice timed problem solving (20 min per problem)",
                    "Review and optimize previous solutions",
                ],
            },
            {
                "phase": 3,
                "name": "Contest & Interview Prep",
                "duration_days": phase3_days,
                "focus": "Contests + Mock interviews + Revision",
                "topics": [{"topic": "Contest Practice", "target_problems": phase3_days * 2}],
                "daily_plan": "Participate in contests + solve 2 random problems + revise weak areas",
                "tips": [
                    "Participate in weekly contests",
                    "Do mock interviews with friends",
                    "Revise patterns and templates",
                    "Focus on speed and accuracy",
                ],
            },
        ],
    }
    
    return roadmap


# =========================================================
# FAANG Readiness
# =========================================================

def estimate_faang_readiness(
    profile: Dict[str, Any],
    topics: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Estimate FAANG interview readiness based on profile and topic stats.
    
    Returns a score 0-100 with breakdown.
    """
    total_solved = profile.get("total_solved", 0)
    easy = profile.get("easy_count", 0)
    medium = profile.get("medium_count", 0)
    hard = profile.get("hard_count", 0)
    contest_rating = profile.get("contest_rating", 0) or profile.get("ranking", 0)
    
    # Score components (each 0-100)
    
    # 1. Volume score (total problems)
    volume_score = min(100, total_solved / 3)  # 300 problems = 100
    
    # 2. Difficulty balance (medium+hard ratio)
    if total_solved > 0:
        difficulty_score = min(100, ((medium + hard * 2) / total_solved) * 150)
    else:
        difficulty_score = 0
    
    # 3. Topic coverage (how many FAANG topics are covered)
    covered_topics = 0
    topic_gaps = []
    for topic_name, minimum in FAANG_TOPIC_MINIMUMS.items():
        solved = 0
        for t in topics:
            if t["topic_name"].lower() == topic_name:
                solved = t["solved_count"]
                break
        if solved >= minimum * 0.5:
            covered_topics += 1
        else:
            topic_gaps.append({"topic": topic_name, "current": solved, "target": minimum})
    
    coverage_score = min(100, (covered_topics / len(FAANG_TOPIC_MINIMUMS)) * 100)
    
    # 4. Contest experience
    contest_score = min(100, contest_rating / 20) if contest_rating > 0 else 0
    
    # Weighted total
    overall = (
        volume_score * 0.25 +
        difficulty_score * 0.25 +
        coverage_score * 0.35 +
        contest_score * 0.15
    )
    
    # Readiness level
    if overall >= 80:
        level = "FAANG Ready"
        message = "You're well-prepared for FAANG interviews!"
    elif overall >= 60:
        level = "Almost Ready"
        message = "Good progress! Focus on weak topics to reach FAANG level."
    elif overall >= 40:
        level = "Building Foundation"
        message = "Keep practicing! You need more problems and topic coverage."
    else:
        level = "Early Stage"
        message = "Focus on building fundamentals first. Start with Easy problems."
    
    return {
        "score": round(overall, 1),
        "level": level,
        "message": message,
        "breakdown": {
            "volume_score": round(volume_score, 1),
            "difficulty_score": round(difficulty_score, 1),
            "topic_coverage_score": round(coverage_score, 1),
            "contest_score": round(contest_score, 1),
        },
        "topic_gaps": sorted(topic_gaps, key=lambda x: x["current"] / max(1, x["target"]))[:8],
    }


def get_interview_readiness_score(
    profile: Dict[str, Any],
    topics: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Calculate detailed interview readiness score."""
    faang = estimate_faang_readiness(profile, topics)
    
    total_solved = profile.get("total_solved", 0)
    easy = profile.get("easy_count", 0)
    medium = profile.get("medium_count", 0)
    hard = profile.get("hard_count", 0)
    
    # Skill balance
    if total_solved > 0:
        easy_ratio = easy / total_solved
        medium_ratio = medium / total_solved
        hard_ratio = hard / total_solved
        
        # Ideal: 30% easy, 50% medium, 20% hard
        balance_score = 100 - (
            abs(easy_ratio - 0.3) * 50 +
            abs(medium_ratio - 0.5) * 50 +
            abs(hard_ratio - 0.2) * 50
        )
    else:
        balance_score = 0
    
    return {
        "overall_score": faang["score"],
        "readiness_level": faang["level"],
        "skill_balance_score": round(max(0, balance_score), 1),
        "difficulty_distribution": {
            "easy": easy,
            "medium": medium,
            "hard": hard,
            "ideal_easy_pct": 30,
            "ideal_medium_pct": 50,
            "ideal_hard_pct": 20,
        },
        "recommendations": faang["topic_gaps"][:5],
    }


def get_daily_recommendations(
    topics: List[Dict[str, Any]],
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate daily practice recommendations."""
    if not topics:
        return {"error": "No topic data available"}
    
    # Find topics needing most attention
    priority_needs = []
    for topic in topics:
        name = topic["topic_name"].lower()
        count = topic["solved_count"]
        faang_min = FAANG_TOPIC_MINIMUMS.get(name, 10)
        gap = max(0, faang_min - count)
        if gap > 0:
            priority_needs.append({
                "topic": topic["topic_name"],
                "gap": gap,
                "current": count,
                "urgency": gap / faang_min if faang_min > 0 else 0,
            })
    
    priority_needs.sort(key=lambda x: x["urgency"], reverse=True)
    
    # Generate daily plan
    total_solved = profile.get("total_solved", 0)
    
    if total_solved < 50:
        focus = "Build foundation with Easy problems"
        daily_count = 3
    elif total_solved < 150:
        focus = "Mix of Easy and Medium problems"
        daily_count = 3
    elif total_solved < 300:
        focus = "Focus on Medium and Hard problems"
        daily_count = 2
    else:
        focus = "Contest prep and Hard problems"
        daily_count = 2
    
    return {
        "daily_problem_count": daily_count,
        "focus_area": focus,
        "priority_topics": [p["topic"] for p in priority_needs[:5]],
        "revision_topics": [t["topic_name"] for t in topics if t["solved_count"] > 0 and t["solved_count"] < 10][:3],
        "recommended_schedule": {
            "warmup": "1 Easy problem (10 min)",
            "main": f"{daily_count - 1} Medium/Hard problems (40 min each)",
            "review": "Review 1 previous solution (15 min)",
        },
    }
