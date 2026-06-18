import os
from dotenv import load_dotenv
from github import Github

load_dotenv()

token = os.getenv("GITHUB_TOKEN")

g = Github(token)

pr_url = input("Enter PR URL: ")

parts = pr_url.split("/")
owner = parts[3]
repo_name = parts[4]
pr_number = int(parts[6])

print(f"URL received: {pr_url}")
print("Owner:", owner)
print("Repository:", repo_name)
print("PR Number:", pr_number)
repo = g.get_repo(f"{owner}/{repo_name}")

pr = repo.get_pull(pr_number)

print("\nPR Found!")
print("Title:", pr.title)
print("Author:", pr.user.login)
print("Base Branch:", pr.base.ref)
print("Head Branch:", pr.head.ref)
print("\nFiles Changed:")

for file in pr.get_files():
    print("\nFile:", file.filename)
    print("Status:", file.status)
    print("Additions:", file.additions)
    print("Deletions:", file.deletions)