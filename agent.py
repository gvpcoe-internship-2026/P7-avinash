# agent.py
import os
from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
from github import Github

from fetch_and_comment import parse_pr_url
from analyzer import analyze_code_with_ruff
from ai_reviewer import generate_ai_review, format_github_comment

load_dotenv()

# ---- STEP 1: DEFINE STATE ----
# This is the "memory" passed between all nodes
class ReviewState(TypedDict):
    pr_url: str
    pr_title: str
    pr_author: str
    pr_number: int
    repo_name: str
    owner: str
    diff_text: str
    ruff_issues: List[str]
    ai_review: str
    final_comment: str
    status: str


# ---- STEP 2: DEFINE NODES ----

def fetch_pr_node(state: ReviewState) -> ReviewState:
    """
    Node 1: Fetches PR details from GitHub
    """
    print("\n🔍 Node 1: Fetching PR from GitHub...")

    token = os.getenv("GITHUB_TOKEN")
    github_client = Github(token)

    owner, repo_name, pr_number = parse_pr_url(state["pr_url"])
    repo = github_client.get_repo(f"{owner}/{repo_name}")
    pr = repo.get_pull(pr_number)

    # Collect all diffs
    all_diffs = []
    for file in pr.get_files():
        if file.patch:
            all_diffs.append(f"### {file.filename}\n{file.patch}")

    diff_text = "\n\n".join(all_diffs)

    print(f"  ✅ PR fetched: {pr.title}")
    print(f"  ✅ Files changed: {pr.changed_files}")

    return {
        **state,
        "pr_title": pr.title,
        "pr_author": pr.user.login,
        "pr_number": pr_number,
        "repo_name": repo_name,
        "owner": owner,
        "diff_text": diff_text,
        "status": "fetched"
    }


def analyze_code_node(state: ReviewState) -> ReviewState:
    """
    Node 2: Runs Ruff static analysis on changed Python files
    """
    print("\n🔧 Node 2: Running Ruff static analysis...")

    token = os.getenv("GITHUB_TOKEN")
    github_client = Github(token)

    repo = github_client.get_repo(f"{state['owner']}/{state['repo_name']}")
    pr = repo.get_pull(state["pr_number"])

    all_issues = []

    for file in pr.get_files():
        if not file.filename.endswith('.py'):
            continue
        if not file.patch:
            continue

        # Extract added lines only
        added_lines = []
        for line in file.patch.splitlines():
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append(line[1:])

        code = "\n".join(added_lines)
        issues = analyze_code_with_ruff(file.filename, code)
        all_issues.extend(issues)

    if all_issues:
        print(f"  ⚠️ Found {len(all_issues)} issue(s)")
    else:
        print("  ✅ No issues found")

    return {
        **state,
        "ruff_issues": all_issues,
        "status": "analyzed"
    }


def generate_review_node(state: ReviewState) -> ReviewState:
    """
    Node 3: Sends diff + ruff issues to Llama 3 for AI review
    """
    print("\n🤖 Node 3: Generating AI review with Llama 3...")

    ai_review = generate_ai_review(
        pr_title=state["pr_title"],
        pr_author=state["pr_author"],
        diff_text=state["diff_text"],
        ruff_issues=state["ruff_issues"]
    )

    final_comment = format_github_comment(ai_review, state["ruff_issues"])

    print("  ✅ AI review generated")

    return {
        **state,
        "ai_review": ai_review,
        "final_comment": final_comment,
        "status": "reviewed"
    }


def post_comment_node(state: ReviewState) -> ReviewState:
    """
    Node 4: Posts the final review comment on the GitHub PR
    """
    print("\n💬 Node 4: Posting comment on GitHub PR...")

    token = os.getenv("GITHUB_TOKEN")
    github_client = Github(token)

    repo = github_client.get_repo(f"{state['owner']}/{state['repo_name']}")
    pr = repo.get_pull(state["pr_number"])

    pr.create_issue_comment(state["final_comment"])

    print("  ✅ Comment posted successfully!")

    return {
        **state,
        "status": "completed"
    }


# ---- STEP 3: BUILD THE GRAPH ----
def build_agent():
    graph = StateGraph(ReviewState)

    # Add all nodes
    graph.add_node("fetch_pr", fetch_pr_node)
    graph.add_node("analyze_code", analyze_code_node)
    graph.add_node("generate_review", generate_review_node)
    graph.add_node("post_comment", post_comment_node)

    # Connect nodes in sequence
    graph.set_entry_point("fetch_pr")
    graph.add_edge("fetch_pr", "analyze_code")
    graph.add_edge("analyze_code", "generate_review")
    graph.add_edge("generate_review", "post_comment")
    graph.add_edge("post_comment", END)

    return graph.compile()


# ---- TEST BLOCK ----
if __name__ == "__main__":
    pr_url = input("Enter PR URL: ").strip()

    print("\n🚀 Starting CodeReview Agent...")
    agent = build_agent()

    result = agent.invoke({
        "pr_url": pr_url,
        "pr_title": "",
        "pr_author": "",
        "pr_number": 0,
        "repo_name": "",
        "owner": "",
        "diff_text": "",
        "ruff_issues": [],
        "ai_review": "",
        "final_comment": "",
        "status": "starting"
    })

    print("\n========== FINAL REVIEW ==========")
    print(result["final_comment"])
    print(f"\n✅ Status: {result['status']}")