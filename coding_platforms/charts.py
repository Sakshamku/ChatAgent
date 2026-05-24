"""
Chart Generation for Coding Analytics.

Creates Plotly charts for topic distribution, difficulty breakdown,
contest rating trends, and progress visualization.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def create_topic_distribution_chart(topics: List[Dict[str, Any]]) -> Optional[dict]:
    """
    Create a pie chart showing topic-wise problem distribution.
    Returns Plotly figure as dict for JSON serialization.
    """
    if not topics:
        return None
    
    # Top 10 topics for readability
    top_topics = sorted(topics, key=lambda x: x["solved_count"], reverse=True)[:10]
    other_count = sum(t["solved_count"] for t in topics[10:]) if len(topics) > 10 else 0
    
    labels = [t["topic_name"] for t in top_topics]
    values = [t["solved_count"] for t in top_topics]
    
    if other_count > 0:
        labels.append("Other")
        values.append(other_count)
    
    fig = {
        "data": [{
            "type": "pie",
            "labels": labels,
            "values": values,
            "hole": 0.4,
            "textinfo": "label+percent",
            "textposition": "outside",
            "marker": {
                "colors": [
                    "#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A",
                    "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52",
                    "#8B9DC3"
                ]
            },
        }],
        "layout": {
            "title": {"text": "Topic Distribution", "font": {"size": 16}},
            "showlegend": True,
            "margin": {"t": 40, "b": 20, "l": 20, "r": 20},
            "height": 400,
        },
    }
    return fig


def create_difficulty_bar_chart(profile: Dict[str, Any]) -> Optional[dict]:
    """
    Create a bar chart showing Easy/Medium/Hard problem breakdown.
    """
    easy = profile.get("easy_count", 0)
    medium = profile.get("medium_count", 0)
    hard = profile.get("hard_count", 0)
    
    if easy == 0 and medium == 0 and hard == 0:
        return None
    
    fig = {
        "data": [{
            "type": "bar",
            "x": ["Easy", "Medium", "Hard"],
            "y": [easy, medium, hard],
            "marker": {
                "color": ["#00CC96", "#FFA15A", "#EF553B"]
            },
            "text": [easy, medium, hard],
            "textposition": "auto",
        }],
        "layout": {
            "title": {"text": "Difficulty Breakdown", "font": {"size": 16}},
            "xaxis": {"title": "Difficulty"},
            "yaxis": {"title": "Problems Solved"},
            "showlegend": False,
            "margin": {"t": 40, "b": 40, "l": 50, "r": 20},
            "height": 350,
        },
    }
    return fig


def create_contest_rating_chart(contests: List[Dict[str, Any]]) -> Optional[dict]:
    """
    Create a line chart showing contest rating trend over time.
    """
    # Filter out the metadata entry
    contest_data = [c for c in contests if c.get("contest_name") != "__current_stats__"]
    
    if not contest_data:
        return None
    
    # Sort by date ascending
    contest_data.sort(key=lambda x: x.get("contest_date", ""))
    
    dates = [c.get("contest_date", "")[:10] for c in contest_data if c.get("contest_date")]
    ratings = [c.get("rating", 0) for c in contest_data if c.get("contest_date")]
    rankings = [c.get("ranking", 0) for c in contest_data if c.get("contest_date")]
    
    if not dates:
        return None
    
    fig = {
        "data": [
            {
                "type": "scatter",
                "mode": "lines+markers",
                "x": dates,
                "y": ratings,
                "name": "Rating",
                "line": {"color": "#636EFA", "width": 2},
                "marker": {"size": 6},
            },
        ],
        "layout": {
            "title": {"text": "Contest Rating Trend", "font": {"size": 16}},
            "xaxis": {"title": "Contest Date", "tickangle": -45},
            "yaxis": {"title": "Rating"},
            "showlegend": True,
            "margin": {"t": 40, "b": 80, "l": 60, "r": 20},
            "height": 400,
        },
    }
    return fig


def create_progress_trend_chart(topics: List[Dict[str, Any]]) -> Optional[dict]:
    """
    Create a horizontal bar chart showing topic-wise progress vs FAANG targets.
    """
    from .analytics import FAANG_TOPIC_MINIMUMS
    
    if not topics:
        return None
    
    # Build comparison data
    topic_names = []
    solved = []
    targets = []
    
    for topic in sorted(topics, key=lambda x: x["solved_count"], reverse=True)[:12]:
        name = topic["topic_name"]
        name_lower = name.lower()
        count = topic["solved_count"]
        target = FAANG_TOPIC_MINIMUMS.get(name_lower, 10)
        
        topic_names.append(name)
        solved.append(count)
        targets.append(target)
    
    if not topic_names:
        return None
    
    fig = {
        "data": [
            {
                "type": "bar",
                "orientation": "h",
                "y": topic_names,
                "x": solved,
                "name": "Solved",
                "marker": {"color": "#00CC96"},
            },
            {
                "type": "bar",
                "orientation": "h",
                "y": topic_names,
                "x": targets,
                "name": "FAANG Target",
                "marker": {"color": "#B6E880"},
                "opacity": 0.5,
            },
        ],
        "layout": {
            "title": {"text": "Topic Progress vs FAANG Targets", "font": {"size": 16}},
            "barmode": "overlay",
            "xaxis": {"title": "Problems"},
            "yaxis": {"autorange": "reversed"},
            "showlegend": True,
            "margin": {"t": 40, "b": 40, "l": 120, "r": 20},
            "height": 500,
        },
    }
    return fig


def create_faang_radar_chart(readiness: Dict[str, Any]) -> Optional[dict]:
    """
    Create a radar/spider chart showing FAANG readiness dimensions.
    """
    breakdown = readiness.get("breakdown", {})
    if not breakdown:
        return None
    
    categories = ["Volume", "Difficulty", "Topic Coverage", "Contest"]
    values = [
        breakdown.get("volume_score", 0),
        breakdown.get("difficulty_score", 0),
        breakdown.get("topic_coverage_score", 0),
        breakdown.get("contest_score", 0),
    ]
    
    # Close the radar
    categories.append(categories[0])
    values.append(values[0])
    
    fig = {
        "data": [{
            "type": "scatterpolar",
            "r": values,
            "theta": categories,
            "fill": "toself",
            "fillcolor": "rgba(99, 110, 250, 0.3)",
            "line": {"color": "#636EFA", "width": 2},
            "name": "Your Score",
        }],
        "layout": {
            "title": {"text": "FAANG Readiness Radar", "font": {"size": 16}},
            "polar": {
                "radialaxis": {"visible": True, "range": [0, 100]},
            },
            "showlegend": True,
            "margin": {"t": 40, "b": 20, "l": 40, "r": 40},
            "height": 400,
        },
    }
    return fig
