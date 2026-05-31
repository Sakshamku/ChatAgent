import json
import os

import pytest
import requests

url = "https://leetcode.com/graphql"
headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

QUERY_TAG_COUNTS_CATEGORY = """
{
  __type(name: "TagProblemCountsCategoryNode") {
    fields {
      name
      type {
        name
        kind
        ofType {
          name
          kind
          ofType {
            name
            kind
          }
        }
      }
    }
  }
}
"""

QUERY_TAG_NODE = """
{
  __type(name: "TagProblemCountNode") {
    fields {
      name
      type {
        name
        kind
        ofType {
          name
          kind
        }
      }
    }
  }
}
"""

QUERY_SKILL_STATS = """
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


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LEETCODE_LIVE_TESTS") != "1",
    reason="Set RUN_LEETCODE_LIVE_TESTS=1 to run live LeetCode API checks.",
)


def _post_graphql(query: str, variables: dict | None = None) -> dict:
    response = requests.post(
        url,
        json={"query": query, "variables": variables or {}},
        headers=headers,
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    assert "errors" not in payload, json.dumps(payload["errors"], indent=2)
    return payload


def test_leetcode_tag_count_schema_supports_skill_stats():
    category_schema = _post_graphql(QUERY_TAG_COUNTS_CATEGORY)
    tag_schema = _post_graphql(QUERY_TAG_NODE)
    skill_stats = _post_graphql(
        QUERY_SKILL_STATS,
        {"username": os.getenv("LEETCODE_TEST_USERNAME", "sakshamkumar352")},
    )

    assert category_schema["data"]["__type"]["fields"]
    assert tag_schema["data"]["__type"]["fields"]
    assert skill_stats["data"]["matchedUser"]["tagProblemCounts"]

