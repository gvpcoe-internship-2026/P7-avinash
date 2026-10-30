# app.py
import streamlit as st
import os
from dotenv import load_dotenv
from github import Github, Auth

from fetch_and_comment import parse_pr_url
from analyzer import analyze_code_with_ruff
from ai_reviewer import generate_ai_review, format_github_comment
from rag import get_style_aware_context

load_dotenv()

# ---- PAGE SETUP ----
st.set_page_config(
    page_title="CodeReview Agent",
    page_icon="🤖",
    layout="wide"
)

# ---- HEADER ----
st.title("🤖 CodeReview Agent")
st.markdown("*AI-powered GitHub PR reviewer using LangGraph, Groq/Llama 3, and RAG*")
st.divider()

# ---- SIDEBAR ----
with st.sidebar:
    st.header("⚙️ Settings")
    post_comment = st.toggle("Post review to GitHub", value=False)
    top_k = st.slider("RAG snippets to use", 1, 5, 3)
    st.divider()
    st.markdown("**Tech Stack:**")
    st.markdown("- 🦜 LangGraph Agent")
    st.markdown("- 🤖 Llama 3.3 via Groq")
    st.markdown("- 🔍 FAISS RAG")
    st.markdown("- 🔧 Ruff Static Analysis")
    st.markdown("- 🐙 GitHub API")

# ---- MAIN INPUT ----
pr_url = st.text_input(
    "Enter GitHub PR URL:",
    placeholder="https://github.com/owner/repo/pull/1"
)

col1, col2 = st.columns([1, 4])
with col1:
    review_button = st.button("🚀 Review PR", type="primary")

# ---- REVIEW PIPELINE ----
if review_button and pr_url:

    try:
        # Step 1: Fetch PR
        with st.status("🔍 Fetching PR from GitHub...", expanded=True) as status:
            token = os.getenv("GITHUB_TOKEN")
            auth = Auth.Token(token)
            github_client = Github(auth=auth)

            owner, repo_name, pr_number = parse_pr_url(pr_url)
            repo = github_client.get_repo(f"{owner}/{repo_name}")
            pr = repo.get_pull(pr_number)

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
            status.update(label="✅ PR fetched!", state="complete")

        # ---- PR STATS ----
        st.subheader("📊 PR Overview")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Files Changed", pr.changed_files)
        m2.metric("Additions", f"+{pr.additions}")
        m3.metric("Deletions", f"-{pr.deletions}")
        m4.metric("Ruff Issues", len(all_issues))

        st.markdown(f"**Title:** {pr.title}")
        st.markdown(f"**Author:** {pr.user.login}")
        st.markdown(f"**URL:** {pr.html_url}")
        st.divider()

        # Step 2: RAG
        with st.status("🔍 Querying repo style history (RAG)...", expanded=True) as status:
            style_context = get_style_aware_context(
                owner, repo_name, diff_text[:500]
            )
            status.update(label="✅ Style context retrieved!", state="complete")

        # Step 3: Generate Review
        with st.status("🤖 Generating AI review with Llama 3...", expanded=True) as status:
            enhanced_diff = f"{diff_text}\n\n## Repo Style Context:\n{style_context}"
            ai_review = generate_ai_review(
                pr_title=pr.title,
                pr_author=pr.user.login,
                diff_text=enhanced_diff,
                ruff_issues=all_issues
            )
            final_comment = format_github_comment(ai_review, all_issues)
            status.update(label="✅ AI review generated!", state="complete")

        # ---- DISPLAY REVIEW ----
        st.subheader("🤖 AI Review")
        st.markdown(final_comment)

        # ---- RUFF ISSUES ----
        if all_issues:
            st.subheader("🔧 Ruff Issues Found")
            for issue in all_issues:
                st.error(issue)
        else:
            st.success("✅ No static analysis issues found!")

        # ---- RAG CONTEXT ----
        with st.expander("📚 Repo Style Context Used (RAG)"):
            st.code(style_context, language="python")

        # ---- DIFF VIEWER ----
        with st.expander("📄 Full PR Diff"):
            st.code(diff_text, language="diff")

        # ---- POST COMMENT ----
        if post_comment:
            with st.status("💬 Posting comment to GitHub...", expanded=True) as status:
                pr.create_issue_comment(final_comment)
                status.update(label="✅ Comment posted!", state="complete")
            st.success("✅ Review posted to GitHub PR!")
        else:
            st.info("💡 Toggle 'Post review to GitHub' in sidebar to auto-post")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

elif review_button and not pr_url:
    st.warning("⚠️ Please enter a PR URL first!")