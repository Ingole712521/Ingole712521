import os
import sys

import requests

USERNAME = os.environ["USERNAME"]
TOKEN = os.environ["GH_TOKEN"]
MAX_ROWS = 20

SEARCH_QUERY = """
query($mergedQuery: String!, $openQuery: String!) {
  merged: search(query: $mergedQuery, type: ISSUE, first: 30) {
    nodes {
      ... on PullRequest {
        number
        title
        url
        merged
        state
        repository {
          nameWithOwner
          owner {
            login
          }
        }
      }
    }
  }
  open: search(query: $openQuery, type: ISSUE, first: 15) {
    nodes {
      ... on PullRequest {
        number
        title
        url
        merged
        state
        repository {
          nameWithOwner
          owner {
            login
          }
        }
      }
    }
  }
}
"""


def graphql(query: str, variables: dict) -> dict:
    response = requests.post(
        "https://api.github.com/graphql",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"query": query, "variables": variables},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]


def is_external_repo(owner_login: str) -> bool:
    return owner_login.lower() != USERNAME.lower()


def add_pr_row(rows: list, seen: set, pr: dict, status: str) -> None:
    repo = pr.get("repository") or {}
    owner = (repo.get("owner") or {}).get("login", "")
    if not is_external_repo(owner):
        return

    name_with_owner = repo.get("nameWithOwner", repo.get("name", "unknown"))
    key = (name_with_owner, pr["number"])
    if key in seen:
        return

    seen.add(key)
    rows.append(
        (
            name_with_owner,
            f"PR #{pr['number']}",
            status,
            pr["url"],
        )
    )


def build_table(rows: list) -> str:
    if not rows:
        return (
            "_No open-source contributions yet. "
            "This section updates automatically when you open or merge PRs in other repos._\n"
        )

    table = "| Project | Contribution | Status |\n"
    table += "|---------|--------------|--------|\n"
    for repo, contribution, status, url in rows:
        table += f"| `{repo}` | [{contribution}]({url}) | {status} |\n"
    return table


def update_readme(table: str) -> bool:
    with open("README.md", encoding="utf-8") as f:
        content = f.read()

    start = "<!-- OSS-CONTRIBUTIONS-START -->"
    end = "<!-- OSS-CONTRIBUTIONS-END -->"

    if start not in content or end not in content:
        print("README markers not found", file=sys.stderr)
        return False

    new_content = (
        content.split(start)[0]
        + start
        + "\n\n"
        + table
        + "\n"
        + end
        + content.split(end, 1)[1]
    )

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_content)

    return True


def main() -> None:
    data = graphql(
        SEARCH_QUERY,
        {
            "mergedQuery": f"author:{USERNAME} is:pr is:merged sort:updated-desc",
            "openQuery": f"author:{USERNAME} is:pr is:open sort:updated-desc",
        },
    )

    rows = []
    seen = set()

    for pr in data["merged"]["nodes"]:
        if pr and pr.get("merged"):
            add_pr_row(rows, seen, pr, "✅ Merged")

    for pr in data["open"]["nodes"]:
        if pr and pr.get("state") == "OPEN":
            add_pr_row(rows, seen, pr, "🟡 Open")

    table = build_table(rows[:MAX_ROWS])

    if update_readme(table):
        print(f"README updated with {min(len(rows), MAX_ROWS)} contribution(s)")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
