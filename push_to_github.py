"""
CareSync Hospital Management System - Automated GitHub Push Utility
Creates a new repository on your GitHub account and uploads all codebase files
directly via the GitHub REST API (No local Git client required).
"""

import os
import sys
import json
import base64
import ssl
import urllib.request
import urllib.error

# Project root directory
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Files/folders to exclude
IGNORE_PATTERNS = [
    ".git", "__pycache__", ".db", "hospital.db", ".log",
    "dashboard_screenshot.png", ".system_generated", "scratch", "browser"
]

def should_ignore(rel_path):
    for pattern in IGNORE_PATTERNS:
        if pattern in rel_path.split(os.sep) or rel_path.endswith(pattern):
            return True
    return False

def make_github_request(url, method="GET", data=None, token=None):
    ctx = ssl._create_unverified_context()
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "CareSync-HMS-Uploader"
    }
    if token:
        headers["Authorization"] = f"token {token}"

    encoded_data = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, context=ctx) as res:
            return json.loads(res.read().decode("utf-8")), res.getcode()
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            err_json = json.loads(err_body)
            return err_json, e.code
        except Exception:
            return {"message": err_body}, e.code

def push_project(token, repo_name="Hospital-Management-System", is_private=False):
    print("=" * 60)
    print("🚀 CareSync HMS -> GitHub Direct Uploader")
    print("=" * 60)

    # 1. Verify User Token
    user_info, code = make_github_request("https://api.github.com/user", token=token)
    if code != 200:
        print(f"❌ Authentication Failed (HTTP {code}): {user_info.get('message', 'Invalid Token')}")
        return False

    username = user_info.get("login")
    print(f"✅ Authenticated as GitHub user: @{username}")

    # 2. Create Repository (if not already existing)
    print(f"📦 Checking repository '{repo_name}' on GitHub...")
    repo_info, code = make_github_request(f"https://api.github.com/repos/{username}/{repo_name}", token=token)

    if code == 404:
        print(f"🔨 Creating new repository '{repo_name}'...")
        repo_payload = {
            "name": repo_name,
            "description": "Hospital Management System website built with Python, Flask, MySQL, SQL, HTML, CSS, JavaScript, and FIFO Waiting Queue",
            "private": is_private,
            "auto_init": True
        }
        repo_info, code = make_github_request("https://api.github.com/user/repos", method="POST", data=repo_payload, token=token)
        if code not in [200, 201]:
            print(f"❌ Failed to create repo: {repo_info.get('message')}")
            return False
        print("✅ Repository created successfully!")
    else:
        print("ℹ️ Repository already exists, committing updates...")

    html_url = repo_info.get("html_url", f"https://github.com/{username}/{repo_name}")

    # 3. Collect Files
    files_to_upload = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, PROJECT_ROOT).replace("\\", "/")
            if not should_ignore(rel_path) and not rel_path.endswith("push_to_github.py"):
                files_to_upload.append((full_path, rel_path))

    print(f"📁 Preparing {len(files_to_upload)} project files for upload...")

    # 4. Create Blobs
    tree_elements = []
    for full_path, rel_path in files_to_upload:
        try:
            with open(full_path, "rb") as f:
                content_bytes = f.read()
                content_b64 = base64.b64encode(content_bytes).decode("utf-8")

            blob_resp, code = make_github_request(
                f"https://api.github.com/repos/{username}/{repo_name}/git/blobs",
                method="POST",
                data={"content": content_b64, "encoding": "base64"},
                token=token
            )
            if code in [200, 201]:
                tree_elements.append({
                    "path": rel_path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_resp["sha"]
                })
                print(f"  + Added: {rel_path}")
            else:
                print(f"  ⚠️ Skipped {rel_path}: {blob_resp.get('message')}")
        except Exception as ex:
            print(f"  ⚠️ Error reading {rel_path}: {ex}")

    # 5. Create Git Tree
    print("🌲 Generating Git Tree...")
    tree_resp, code = make_github_request(
        f"https://api.github.com/repos/{username}/{repo_name}/git/trees",
        method="POST",
        data={"tree": tree_elements},
        token=token
    )
    if code not in [200, 201]:
        print(f"❌ Failed to create tree: {tree_resp.get('message')}")
        return False
    tree_sha = tree_resp["sha"]

    # 6. Get Parent Commit (HEAD of main)
    ref_resp, code = make_github_request(
        f"https://api.github.com/repos/{username}/{repo_name}/git/refs/heads/main",
        token=token
    )
    parent_sha = None
    if code == 200:
        parent_sha = ref_resp["object"]["sha"]

    # 7. Create Commit
    print("💾 Creating Git Commit...")
    commit_payload = {
        "message": "Initial release: Complete Hospital Management System with Flask, MySQL, and FIFO Waiting Queue",
        "tree": tree_sha,
        "parents": [parent_sha] if parent_sha else []
    }
    commit_resp, code = make_github_request(
        f"https://api.github.com/repos/{username}/{repo_name}/git/commits",
        method="POST",
        data=commit_payload,
        token=token
    )
    if code not in [200, 201]:
        print(f"❌ Failed to create commit: {commit_resp.get('message')}")
        return False
    commit_sha = commit_resp["sha"]

    # 8. Update Reference (branch main)
    print("🚀 Pushing to main branch...")
    if parent_sha:
        update_ref, code = make_github_request(
            f"https://api.github.com/repos/{username}/{repo_name}/git/refs/heads/main",
            method="PATCH",
            data={"sha": commit_sha, "force": True},
            token=token
        )
    else:
        update_ref, code = make_github_request(
            f"https://api.github.com/repos/{username}/{repo_name}/git/refs",
            method="POST",
            data={"ref": "refs/heads/main", "sha": commit_sha},
            token=token
        )

    print("\n" + "=" * 60)
    print(f"🎉 SUCCESS! All code pushed directly to GitHub:")
    print(f"👉 {html_url}")
    print("=" * 60)
    return True

if __name__ == "__main__":
    token = os.getenv("GITHUB_TOKEN")
    if len(sys.argv) > 1:
        token = sys.argv[1]

    if not token:
        print("\n🔑 GitHub Personal Access Token (PAT) Required:")
        print("1. Go to: https://github.com/settings/tokens (classic) or fine-grained tokens.")
        print("2. Generate a token with 'repo' scope permissions.")
        print("3. Run: python push_to_github.py <YOUR_GITHUB_TOKEN>\n")
    else:
        repo = sys.argv[2] if len(sys.argv) > 2 else "Hospital-Management-System"
        push_project(token, repo)
