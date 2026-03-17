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
