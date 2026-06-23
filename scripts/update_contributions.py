import os
import requests

USERNAME = os.environ["USERNAME"]
TOKEN = os.environ["GH_TOKEN"]

query = """
query($login: String!) {
  user(login: $login) {

    pullRequests(
      first: 100,
      orderBy: {field: CREATED_AT, direction: DESC}
    ) {
      nodes {
        number
        title
        merged
        state
        url

        repository {
          name
        }
      }
    }

    issues(
      first: 50,
      orderBy: {field: CREATED_AT, direction: DESC}
    ) {
      nodes {
        number
        state
        url

        repository {
          name
        }
      }
    }
  }
}
"""

response = requests.post(
    "https://api.github.com/graphql",
    headers={
        "Authorization": f"Bearer {TOKEN}"
    },
    json={
        "query": query,
        "variables": {
            "login": USERNAME
        }
    }
)

data = response.json()

prs = data["data"]["user"]["pullRequests"]["nodes"]
issues = data["data"]["user"]["issues"]["nodes"]

rows = []

# merged/open PRs
for pr in prs:

    if pr["merged"]:
        status = "✅ Merged"
    elif pr["state"] == "OPEN":
        status = "🟡 Open"
    else:
        continue

    rows.append(
        (
            pr["repository"]["name"],
            f"PR #{pr['number']}",
            status,
            pr["url"]
        )
    )

# closed issues
for issue in issues:

    if issue["state"] != "CLOSED":
        continue

    rows.append(
        (
            issue["repository"]["name"],
            f"Issue #{issue['number']}",
            "✔ Closed",
            issue["url"]
        )
    )

rows = rows[:20]

table = """
| Project | Contribution | Status |
|---------|--------------|--------|
"""

for repo, contribution, status, url in rows:
    table += (
        f"| {repo} "
        f"| [{contribution}]({url}) "
        f"| {status} |\n"
    )

with open("README.md", encoding="utf-8") as f:
    content = f.read()

start = "<!-- OSS-CONTRIBUTIONS-START -->"
end = "<!-- OSS-CONTRIBUTIONS-END -->"

new_content = (
    content.split(start)[0]
    + start
    + "\n\n"
    + table
    + "\n"
    + end
    + content.split(end)[1]
)

with open("README.md", "w", encoding="utf-8") as f:
    f.write(new_content)

print("README updated")
