# ai_reviewer.py
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_ai_review(pr_title, pr_author, diff_text, ruff_issues):
    """
    Sends PR diff + Ruff issues to Llama 3 via Groq
    and gets back a structured code review.
    """

    # Format ruff issues for the prompt
    if ruff_issues:
        ruff_summary = "\n".join(ruff_issues)
    else:
        ruff_summary = "No static analysis issues found."

    prompt = f"""You are an expert code reviewer. Review this GitHub Pull Request and provide structured feedback.

PR Title: {pr_title}
Author: {pr_author}

Static Analysis Results (Ruff):
{ruff_summary}

Code Changes (Diff):
{diff_text[:3000]}

Provide a structured review with these exact sections:

## Summary
Brief overview of what this PR does.

## Issues Found
List any bugs, security issues, or bad practices with line numbers if possible.

## Code Quality
Comment on readability, structure, and style.

## Suggestions
Specific actionable improvements.

## Verdict
One of: APPROVE / REQUEST CHANGES / NEEDS DISCUSSION
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a senior software engineer doing thorough code reviews. Be specific, helpful and constructive."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=1024,
        temperature=0.3  # lower = more focused, less random
    )

    return response.choices[0].message.content


def format_github_comment(ai_review, ruff_issues):
    """
    Formats the final comment to post on GitHub PR.
    """
    ruff_section = ""
    if ruff_issues:
        ruff_section = "## 🔍 Static Analysis Issues\n"
        for issue in ruff_issues:
            ruff_section += f"- `{issue}`\n"
    else:
        ruff_section = "## 🔍 Static Analysis\n✅ No issues found by Ruff\n"

    comment = f"""# 🤖 AI Code Review — CodeReview Agent

{ruff_section}

---

{ai_review}

---
*Posted by CodeReview-Agent | Powered by Llama 3.3 via Groq*
"""
    return comment


# ---- TEST BLOCK ----
if __name__ == "__main__":
    # Test with fake data first
    test_diff = """
+def login(username, password):
+    query = f"SELECT * FROM users WHERE user='{username}'"
+    import os
+    import sys
+    x = 1+1
+    return query
"""
    test_ruff_issues = [
        "auth.py:3:5: F401 'os' imported but unused",
        "auth.py:4:5: F401 'sys' imported but unused",
    ]

    print("Generating AI review...")
    review = generate_ai_review(
        pr_title="Add login function",
        pr_author="testuser",
        diff_text=test_diff,
        ruff_issues=test_ruff_issues
    )

    print(format_github_comment(review, test_ruff_issues))