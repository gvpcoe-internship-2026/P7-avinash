# rag.py
import os
import numpy as np
from github import Github
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import faiss

load_dotenv()

# Load embedding model (same one from StudyMate!)
print("Loading embedding model...")
embedder = SentenceTransformer("all-MiniLM-L6-v2")
print("Embedding model ready!")


def fetch_repo_history(owner, repo_name, max_commits=20):
    """
    Fetches recent commits from the repo and extracts
    code snippets to build a style knowledge base.
    """
    print(f"\n📚 Fetching repo history ({max_commits} commits)...")

    token = os.getenv("GITHUB_TOKEN")
    github_client = Github(token)
    repo = github_client.get_repo(f"{owner}/{repo_name}")

    code_snippets = []

    commits = list(repo.get_commits()[:max_commits])

    for commit in commits:
        try:
            files = commit.files
            for file in files:
                # Only Python files with actual changes
                if file.filename.endswith('.py') and file.patch:
                    # Extract added lines
                    added = []
                    for line in file.patch.splitlines():
                        if line.startswith('+') and not line.startswith('+++'):
                            added.append(line[1:])

                    if len(added) > 3:  # only meaningful snippets
                        snippet = "\n".join(added[:20])  # first 20 lines
                        code_snippets.append({
                            "file": file.filename,
                            "commit": commit.sha[:7],
                            "code": snippet
                        })
        except Exception:
            continue  # skip commits with no files

    print(f"  ✅ Collected {len(code_snippets)} code snippets")
    return code_snippets


def build_style_index(code_snippets):
    """
    Embeds all code snippets and builds a FAISS index
    for semantic style search.
    """
    if not code_snippets:
        print("  ⚠️ No snippets to index")
        return None, []

    print("\n🔨 Building style index...")

    texts = [s["code"] for s in code_snippets]
    embeddings = embedder.encode(texts, show_progress_bar=True)
    embeddings = np.array(embeddings, dtype="float32")

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    print(f"  ✅ Indexed {index.ntotal} code snippets")
    return index, code_snippets


def query_style_context(query, index, snippets, top_k=3):
    """
    Given a piece of code, finds the most similar
    historical code snippets for style context.
    """
    if index is None or not snippets:
        return "No repo history available for style context."

    query_vector = embedder.encode([query])
    query_vector = np.array(query_vector, dtype="float32")

    distances, indices = index.search(query_vector, top_k)

    results = []
    for i in indices[0]:
        if i < len(snippets):
            s = snippets[i]
            results.append(
                f"# From {s['file']} (commit {s['commit']})\n{s['code']}"
            )

    return "\n\n---\n\n".join(results)


def get_style_aware_context(owner, repo_name, pr_diff):
    """
    Main function: builds style index from repo history
    and finds relevant style examples for the PR diff.
    """
    snippets = fetch_repo_history(owner, repo_name)

    if not snippets:
        return "No Python history found in this repo."

    index, snippets = build_style_index(snippets)
    style_context = query_style_context(pr_diff[:500], index, snippets)

    return style_context


# ---- TEST BLOCK ----
if __name__ == "__main__":
    owner = input("GitHub owner (e.g. gvpcoe-internship-2026): ").strip()
    repo = input("Repo name (e.g. P7-avinash): ").strip()

    test_diff = "def review_pr(url): pass"

    print("\n🔍 Finding similar code style from repo history...")
    context = get_style_aware_context(owner, repo, test_diff)

    print("\n========== STYLE CONTEXT ==========")
    print(context)