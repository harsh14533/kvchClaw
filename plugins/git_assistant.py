# plugins/git_assistant.py
# Git Workflow Assistant
# Manage all your git repos from Telegram or terminal

import os
import subprocess
from datetime import datetime
from plugins.base import Plugin

# Your actual repo locations
SEARCH_PATHS = [
    os.path.expanduser("~"),
    os.path.expanduser("~/GitDemo"),
]
MAX_DEPTH = 4

# Repos to ignore
IGNORE_REPOS = [
    ".nvm", ".cargo", ".rustup", ".local"
]

def find_git_repos():
    repos = []
    seen = set()
    for search_path in SEARCH_PATHS:
        if not os.path.exists(search_path):
            continue
        try:
            result = subprocess.run(
                "find " + search_path + " -name .git -maxdepth " + str(MAX_DEPTH) + " -type d 2>/dev/null",
                shell=True, capture_output=True, text=True
            )
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                repo_path = line.replace("/.git", "")
                skip = False
                for ignore in IGNORE_REPOS:
                    if ignore in repo_path:
                        skip = True
                        break
                if skip:
                    continue
                if repo_path == os.path.expanduser("~"):
                    continue
                if repo_path not in seen:
                    seen.add(repo_path)
                    repos.append(repo_path)
        except:
            pass
    return repos

def run_git(command, cwd):
    try:
        result = subprocess.run(
            "git " + command,
            shell=True, capture_output=True,
            text=True, cwd=cwd, timeout=15
        )
        return result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return "", str(e)

def get_repo_name(path):
    return os.path.basename(path)

def get_repo_status(repo_path):
    name = get_repo_name(repo_path)
    status = {"name": name, "path": repo_path, "issues": []}

    out, _ = run_git("status --porcelain", repo_path)
    if out:
        lines = out.strip().split("\n")
        modified = [l for l in lines if l.startswith(" M") or l.startswith("M")]
        untracked = [l for l in lines if l.startswith("??")]
        staged = [l for l in lines if l.startswith("A") or l.startswith("AM")]
        if modified:
            status["issues"].append(str(len(modified)) + " modified files")
        if untracked:
            status["issues"].append(str(len(untracked)) + " untracked files")
        if staged:
            status["issues"].append(str(len(staged)) + " staged files")

    branch, _ = run_git("branch --show-current", repo_path)
    status["branch"] = branch or "unknown"

    run_git("fetch --quiet 2>/dev/null", repo_path)
    behind, _ = run_git("rev-list HEAD..@{upstream} --count 2>/dev/null", repo_path)
    ahead, _ = run_git("rev-list @{upstream}..HEAD --count 2>/dev/null", repo_path)

    if behind and behind.isdigit() and int(behind) > 0:
        status["issues"].append(behind + " commits behind remote")
    if ahead and ahead.isdigit() and int(ahead) > 0:
        status["issues"].append(ahead + " unpushed commits")

    last_commit, _ = run_git("log -1 --format=%ar: %s 2>/dev/null", repo_path)
    status["last_commit"] = last_commit or "no commits yet"

    return status

def get_all_status():
    repos = find_git_repos()
    if not repos:
        return "No git repositories found."

    result = "*Git Status — " + str(len(repos)) + " repos*\n\n"
    has_issues = []
    clean = []

    for repo_path in repos:
        status = get_repo_status(repo_path)
        if status["issues"]:
            has_issues.append(status)
        else:
            clean.append(status)

    if has_issues:
        result += "*Needs attention:*\n"
        for s in has_issues:
            result += "\n" + s["name"] + " [" + s["branch"] + "]\n"
            for issue in s["issues"]:
                result += "  - " + issue + "\n"
            result += "  Last: " + s["last_commit"][:60] + "\n"

    if clean:
        result += "\n*Clean repos (" + str(len(clean)) + "):* "
        result += ", ".join([s["name"] for s in clean])

    return result

def generate_smart_commit_message(repo_path):
    diff, _ = run_git("diff --staged --stat", repo_path)
    if not diff:
        diff, _ = run_git("diff --stat", repo_path)
    if not diff:
        return "update: minor changes"

    lines = diff.strip().split("\n")
    changed_files = []
    for line in lines[:-1]:
        parts = line.strip().split("|")
        if parts:
            fname = parts[0].strip()
            if fname:
                changed_files.append(fname)

    if not changed_files:
        return "update: changes made"

    file_count = len(changed_files)
    main_file = os.path.basename(changed_files[0])
    extensions = set([os.path.splitext(f)[1] for f in changed_files])

    if file_count == 1:
        return "update: modify " + main_file
    elif ".py" in extensions:
        return "update: modify " + str(file_count) + " files including " + main_file
    elif ".md" in extensions and file_count == 1:
        return "docs: update " + main_file
    else:
        return "update: modify " + str(file_count) + " files"

def smart_commit(repo_path, message=None):
    name = get_repo_name(repo_path)
    out, _ = run_git("status --porcelain", repo_path)
    if not out:
        return "Nothing to commit in " + name

    run_git("add .", repo_path)

    if not message:
        message = generate_smart_commit_message(repo_path)

    out, err = run_git('commit -m "' + message + '"', repo_path)
    if "nothing to commit" in err:
        return "Nothing to commit in " + name
    if out:
        return "Committed in " + name + ":\n" + message
    return "Error: " + err

def push_repo(repo_path):
    name = get_repo_name(repo_path)
    out, err = run_git("push", repo_path)
    if "Everything up-to-date" in err:
        return name + " is already up to date"
    if out:
        return "Pushed " + name + " successfully"
    return "Push result: " + (out or err)

def show_todays_changes(repo_path):
    name = get_repo_name(repo_path)
    out, _ = run_git('log --since=midnight --oneline --stat', repo_path)
    if not out:
        return "No commits today in " + name
    return "*" + name + " today:*\n" + out[:1500]

def find_repo_by_name(name):
    repos = find_git_repos()
    name_lower = name.lower().strip()
    for repo in repos:
        if name_lower in get_repo_name(repo).lower():
            return repo
    return None

class GitAssistantPlugin(Plugin):
    name = "GIT_ASSISTANT"
    description = (
        "Git workflow assistant. Check status of all git repos, "
        "commit changes with smart messages, push to remote, "
        "create branches, show today's changes across all projects."
    )
    triggers = [
        "git", "commit", "push", "branch", "repo", "repos",
        "git status", "my projects", "unpushed", "uncommitted",
        "what changed", "changes today", "create branch",
        "all repos", "show repos", "project status", "pull"
    ]

    def execute(self, value: str) -> tuple:
        try:
            val = value.lower().strip()

            # Status of all repos
            if any(w in val for w in [
                "status", "all repos", "my projects",
                "show repos", "project status",
                "unpushed", "uncommitted", "behind"
            ]):
                return get_all_status(), None

            # Today's changes
            if "today" in val or "what changed" in val:
                repos = find_git_repos()
                if not repos:
                    return "No git repos found", None
                for repo in repos:
                    if get_repo_name(repo).lower() in val:
                        return show_todays_changes(repo), None
                myclaw = find_repo_by_name("myclaw")
                target = myclaw or repos[0]
                return show_todays_changes(target), None

            # Create branch
            if "create branch" in val or "new branch" in val:
                words = value.strip().split()
                branch_name = None
                for i, word in enumerate(words):
                    if word.lower() in ["branch", "called", "named"]:
                        if i + 1 < len(words):
                            branch_name = words[i + 1]
                            break
                if not branch_name:
                    branch_name = "feature/new-" + datetime.now().strftime("%m%d")
                repos = find_git_repos()
                repo = find_repo_by_name("myclaw") or (repos[0] if repos else None)
                if repo:
                    out, err = run_git("checkout -b " + branch_name, repo)
                    if "Switched to" in out:
                        return "Created branch " + branch_name + " in " + get_repo_name(repo), None
                    return "Error: " + err, None
                return "No git repos found", None

            # Commit
            if "commit" in val:
                repos = find_git_repos()
                target_repo = None
                custom_message = None
                for repo in repos:
                    if get_repo_name(repo).lower() in val:
                        target_repo = repo
                        break
                if "message" in val:
                    parts = value.split("message")
                    if len(parts) > 1:
                        custom_message = parts[1].strip().strip('"').strip("'")
                if not target_repo:
                    target_repo = find_repo_by_name("myclaw") or (repos[0] if repos else None)
                if target_repo:
                    return smart_commit(target_repo, custom_message), None
                return "No git repos found", None

            # Push
            if "push" in val:
                repos = find_git_repos()
                target_repo = None
                for repo in repos:
                    if get_repo_name(repo).lower() in val:
                        target_repo = repo
                        break
                if not target_repo:
                    target_repo = find_repo_by_name("myclaw") or (repos[0] if repos else None)
                if target_repo:
                    return push_repo(target_repo), None
                return "No git repos found", None

            # Pull
            if "pull" in val:
                repos = find_git_repos()
                target_repo = None
                for repo in repos:
                    if get_repo_name(repo).lower() in val:
                        target_repo = repo
                        break
                if not target_repo:
                    target_repo = find_repo_by_name("myclaw") or (repos[0] if repos else None)
                if target_repo:
                    out, err = run_git("pull", target_repo)
                    return out or err or "Pulled successfully", None
                return "No git repos found", None

            # Default — list all repos
            repos = find_git_repos()
            if not repos:
                return "No git repos found", None
            repo_list = "*Your git repos:*\n"
            for repo in repos:
                branch, _ = run_git("branch --show-current", repo)
                repo_list += "\n- " + get_repo_name(repo) + " [" + (branch or "unknown") + "]\n  " + repo
            return repo_list, None

        except Exception as e:
            return "Git assistant error: " + str(e), None
