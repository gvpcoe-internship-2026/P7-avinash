# analyzer.py
import subprocess
import tempfile
import os
from github import Github
from dotenv import load_dotenv

load_dotenv()


def analyze_code_with_ruff(filename, code_content):
    """
    Runs Ruff on a piece of code and returns list of issues found.
    """
    issues = []

    # Write code to a temporary file (Ruff needs a real file to analyze)
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.py',
        delete=False,
        encoding='utf-8'
    ) as tmp:
        tmp.write(code_content)
        tmp_path = tmp.name

    try:
        # Run Ruff on the temp file
        result = subprocess.run(
            ["ruff", "check", tmp_path, "--output-format=text"],
            capture_output=True,
            text=True
        )

        # Parse each line of ruff output
        for line in result.stdout.splitlines():
            if tmp_path in line:
                # Replace temp path with real filename for clarity
                clean_line = line.replace(tmp_path, filename)
                issues.append(clean_line)

    finally:
        os.unlink(tmp_path)  # always delete temp file

    return issues


def get_pr_files_and_analyze(pr_url):
    """
    Fetches all changed Python files from a PR
    and runs Ruff analysis on each one.
    """
    from fetch_and_comment import parse_pr_url

    token = os.getenv("GITHUB_TOKEN")
    github_client = Github(token)

    owner, repo_name, pr_number = parse_pr_url(pr_url)
    repo = github_client.get_repo(f"{owner}/{repo_name}")
    pr = repo.get_pull(pr_number)

    print(f"\nAnalyzing PR: {pr.title}")
    print(f"Files changed: {pr.changed_files}\n")

    analysis_results = {}  # filename → list of issues

    for file in pr.get_files():
        # Only analyze Python files
        if not file.filename.endswith('.py'):
            print(f"Skipping non-Python file: {file.filename}")
            continue

        if not file.patch:
            print(f"No diff available for: {file.filename}")
            continue

        # Extract only added lines (lines starting with +)
        added_lines = []
        for line in file.patch.splitlines():
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append(line[1:])  # remove the + prefix

        code_to_analyze = "\n".join(added_lines)

        print(f"Analyzing: {file.filename}")
        issues = analyze_code_with_ruff(file.filename, code_to_analyze)
        analysis_results[file.filename] = issues

        if issues:
            print(f"  Found {len(issues)} issue(s):")
            for issue in issues:
                print(f"    {issue}")
        else:
            print(f"  No issues found ✅")

    return analysis_results, pr


# ---- TEST BLOCK ----
if __name__ == "__main__":
    pr_url = input("Enter PR URL: ").strip()
    results, pr = get_pr_files_and_analyze(pr_url)

    print("\n========== SUMMARY ==========")
    total_issues = sum(len(v) for v in results.values())
    print(f"Total files analyzed: {len(results)}")
    print(f"Total issues found: {total_issues}")