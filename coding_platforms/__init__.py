"""
Coding Platform Analytics Package.

Integrates with LeetCode and GeeksforGeeks to provide
AI-powered coding profile analytics, roadmaps, and visualizations.
"""

from .leetcode import fetch_leetcode_profile, fetch_leetcode_topics, fetch_leetcode_contests
from .gfg import fetch_gfg_profile, scrape_gfg_stats
from .analytics import (
    analyze_topics, get_weakest_topic, get_strongest_topic,
    generate_dsa_roadmap, estimate_faang_readiness, get_interview_readiness_score,
    get_daily_recommendations
)
from .charts import (
    create_topic_distribution_chart, create_difficulty_bar_chart,
    create_contest_rating_chart, create_progress_trend_chart
)
