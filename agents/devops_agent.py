from git import Repo, InvalidGitRepositoryError


def commit_code(message="AI generated code commit"):
    """
    DevOps Agent:
    Commits all changes to the local git repository.
    """
    try:
        repo = Repo(".")
    except InvalidGitRepositoryError:
        return {"status": "error", "reason": "Not a git repository"}

    if not repo.is_dirty(untracked_files=True):
        return {"status": "skipped", "reason": "No changes to commit"}

    repo.git.add(all=True)
    repo.index.commit(message)

    return {"status": "committed", "message": message}


def push_code(remote="origin", branch="main"):
    """
    Push Agent:
    Pushes the committed code to the remote GitHub repository.
    """
    try:
        repo = Repo(".")
    except InvalidGitRepositoryError:
        return {"status": "error", "reason": "Not a git repository"}

    remotes = [r.name for r in repo.remotes]
    if remote not in remotes:
        return {"status": "error", "reason": f"Remote '{remote}' not found"}

    repo.git.push(remote, branch)

    remote_url = repo.remotes[remote].url
    return {
        "status": "pushed",
        "remote": remote,
        "branch": branch,
        "url": remote_url
    }
