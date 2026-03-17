from git import Repo


def commit_code(message="AI generated code commit"):
    """
    DevOps Agent:
    Commits all changes to git
    """

    repo = Repo(".")

    repo.git.add(all=True)

    repo.index.commit(message)

    return {"status": "committed"}