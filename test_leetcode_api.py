"""Quick test script for LeetCode API"""
import requests
import json

url = "https://leetcode.com/graphql"
headers = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Introspect the nested type
query = """
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
resp = requests.post(url, json={"query": query}, headers=headers, timeout=15)
print(f"Introspection 1: {json.dumps(resp.json(), indent=2)[:3000]}")

# Introspect the tag node type
query2 = """
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
resp2 = requests.post(url, json={"query": query2}, headers=headers, timeout=15)
print(f"\nIntrospection 2: {json.dumps(resp2.json(), indent=2)[:3000]}")

# Try the actual query with nested fields
query3 = """
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
resp3 = requests.post(url, json={"query": query3, "variables": {"username": "sakshamkumar352"}}, headers=headers, timeout=15)
print(f"\nActual Query Status: {resp3.status_code}")
print(json.dumps(resp3.json(), indent=2)[:3000])

