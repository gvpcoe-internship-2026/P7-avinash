from github import Github
from urllib.parse import urlparse
import os
from dotenv import load_dotenv

load_dotenv()


def parse_pr_url(pr_url):
    """
    Example:
    https://github.com/owner/repo/pull/1
    """
    parts = urlparse(pr_url).path.strip("/").split("/")

    owner = parts[0]
    repo = parts[1]
    pr_number = int(parts[3])

    return owner, repo, pr_number


def main():
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        print("GITHUB_TOKEN not found")
        return

    pr_url = input("Enter PR URL: ").strip()

    owner, repo_name, pr_number = parse_pr_url(pr_url)

    github_client = Github(token)
    repo = github_client.get_repo(f"{owner}/{repo_name}")
    pr = repo.get_pull(pr_number)

    print(f"\nPR Title: {pr.title}")
    print(f"Author: {pr.user.login}")
    print(f"Files Changed: {pr.changed_files}")

    if pr.changed_files > 50:
        print("PR has more than 50 files. Skipping.")
        return

    files = pr.get_files()

    print("\n========== DIFFS ==========")

    for file in files:
        print(f"\nFile: {file.filename}")

        if file.patch:
            diff_lines = file.patch.splitlines()

            print("First 20 diff lines:")

            for line in diff_lines[:20]:
                print(line)
        else:
            print("No diff available.")

    comment = (
        "Automated comment from CodeReview-Agent prototype.\n"
        f"Reviewed {pr.changed_files} files. "
        "Posted by AnnepuAvinash0."
    )

    print("\nComment to be posted:")
    print(comment)
    print("Authenticated as:", github_client.get_user().login)
    print(repo.permissions)
    # Uncomment after testing
    pr.create_issue_comment(comment)

    print("\nComment posted successfully.")


if __name__ == "__main__":
    main()