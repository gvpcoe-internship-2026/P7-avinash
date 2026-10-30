# mcp_server.py
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from github import Github, Auth

from fetch_and_comment import parse_pr_url
from analyzer import analyze_code_with_ruff
from ai_reviewer import generate_ai_review, format_github_comment
from rag import get_style_aware_context

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("CodeReview-Agent")


@mcp.tool()
def review_pull_request(pr_url: str, post_comment: bool = True) -> str:
    """
    Reviews a GitHub Pull Request using AI.
    Runs static analysis, checks code style,
    generates structured review and optionally posts it.

    Args:
        pr_url: Full GitHub PR URL
        post_comment: Whether to post review as GitHub comment
    """
    try:
        print(f"\n🚀 MCP: Reviewing PR: {pr_url}")

        # Step 1: Fetch PR
        token = os.getenv("GITHUB_TOKEN")
        auth = Auth.Token(token)
        github_client = Github(auth=auth)

        owner, repo_name, pr_number = parse_pr_url(pr_url)
        repo = github_client.get_repo(f"{owner}/{repo_name}")
        pr = repo.get_pull(pr_number)

        print(f"  ✅ PR fetched: {pr.title}")

        # Step 2: Collect diffs
        all_diffs = []
        all_issues = []

        for file in pr.get_files():
            if file.patch:
                all_diffs.append(f"### {file.filename}\n{file.patch}")

            if file.filename.endswith('.py') and file.patch:
                added_lines = []
                for line in file.patch.splitlines():
                    if line.startswith('+') and not line.startswith('+++'):
                        added_lines.append(line[1:])

                code = "\n".join(added_lines)
                issues = analyze_code_with_ruff(file.filename, code)
                all_issues.extend(issues)

        diff_text = "\n\n".join(all_diffs)
        print(f"  ✅ Ruff found {len(all_issues)} issues")

        # Step 3: Get style context from RAG
        print("  🔍 Querying repo style history...")
        style_context = get_style_aware_context(
            owner, repo_name, diff_text[:500]
        )

        # Step 4: Generate AI review
        print("  🤖 Generating AI review...")
        enhanced_diff = f"{diff_text}\n\n## Repo Style Context:\n{style_context}"

        ai_review = generate_ai_review(
            pr_title=pr.title,
            pr_author=pr.user.login,
            diff_text=enhanced_diff,
            ruff_issues=all_issues
        )

        final_comment = format_github_comment(ai_review, all_issues)

        # Step 5: Post comment if requested
        if post_comment:
            pr.create_issue_comment(final_comment)
            print("  ✅ Comment posted!")

        return final_comment

    except Exception as e:
        return f"Error reviewing PR: {str(e)}"


@mcp.tool()
def get_pr_summary(pr_url: str) -> str:
    """
    Gets a quick summary of a GitHub PR without posting a comment.

    Args:
        pr_url: Full GitHub PR URL
    """
    try:
        token = os.getenv("GITHUB_TOKEN")
        auth = Auth.Token(token)
        github_client = Github(auth=auth)

        owner, repo_name, pr_number = parse_pr_url(pr_url)
        repo = github_client.get_repo(f"{owner}/{repo_name}")
        pr = repo.get_pull(pr_number)

        summary = f"""
## PR Summary
- **Title:** {pr.title}
- **Author:** {pr.user.login}
- **Files Changed:** {pr.changed_files}
- **Additions:** +{pr.additions}
- **Deletions:** -{pr.deletions}
- **State:** {pr.state}
- **URL:** {pr.html_url}
        """
        return summary

    except Exception as e:
        return f"Error fetching PR: {str(e)}"


# ---- TEST BLOCK ----
if __name__ == "__main__":
    print("🚀 Starting CodeReview-Agent MCP Server...")
    print("Tools available:")
    print("  - review_pull_request(pr_url, post_comment)")
    print("  - get_pr_summary(pr_url)")
    print("\nServer running on http://localhost:8000")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)