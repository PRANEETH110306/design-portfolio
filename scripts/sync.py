
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Find the Portfolio folder automatically
PROJECT_DIR = Path(__file__).resolve().parent.parent

# Files that should never be uploaded
BLOCKED_NAMES = {
    ".env",
    "id_rsa",
    "id_ed25519",
}

BLOCKED_EXTENSIONS = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


def run_git(arguments, check=True):
    return subprocess.run(
        ["git", *arguments],
        cwd=PROJECT_DIR,
        check=check,
        text=True,
        capture_output=True
    )


def stop(message):
    print(f"\nERROR: {message}")
    sys.exit(1)


def main():
    print("================================")
    print("       PARK CREATIONS SYNC")
    print("================================\n")

    if not (PROJECT_DIR / ".git").exists():
        stop("Git repository not found.")

    # Confirm Git is available
    try:
        run_git(["--version"])
    except FileNotFoundError:
        stop(
            "Git command not found. "
            "Please ensure Git is installed and available in PATH."
        )

    # Identify modified, staged and untracked files
    changed = set()

    tracked = run_git(
        ["diff", "--name-only", "HEAD"],
        check=False
    )
    if tracked.returncode == 0:
        changed.update(
            line for line in tracked.stdout.splitlines() if line
        )

    untracked = run_git(
        ["ls-files", "--others", "--exclude-standard"]
    )
    changed.update(
        line for line in untracked.stdout.splitlines() if line
    )

    # Safety checks before staging
    for relative_path in changed:
        file_path = PROJECT_DIR / relative_path

        filename = file_path.name.lower()
        extension = file_path.suffix.lower()

        if filename in BLOCKED_NAMES:
            stop(f"Potentially sensitive file detected: {relative_path}")

        if filename.startswith(".env.") and filename != ".env.example":
            stop(f"Potentially sensitive file detected: {relative_path}")

        if extension in BLOCKED_EXTENSIONS:
            stop(f"Potential private key or certificate: {relative_path}")

        if file_path.is_file() and file_path.stat().st_size >= MAX_FILE_SIZE:
            stop(f"File is 100 MB or larger: {relative_path}")

    # Stage all changes
    print("Adding portfolio changes...")
    run_git(["add", "-A"])

    # Check whether there is anything to commit
    result = run_git(
        ["diff", "--cached", "--quiet"],
        check=False
    )

    if result.returncode == 0:
        print("\nNo new changes to synchronize.")
        return

    if result.returncode != 1:
        stop("Could not check staged changes.")

    # Ask for a commit message
    default_message = (
        "Portfolio update " + datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    message = input(
        f"\nEnter commit message [{default_message}]: "
    ).strip()

    if not message:
        message = default_message

    # Commit changes
    print("\nCommitting changes...")
    run_git(["commit", "-m", message])

    # Identify current branch
    branch = run_git(
        ["branch", "--show-current"]
    ).stdout.strip()

    if not branch:
        stop("Could not identify the current Git branch.")

    # Push to GitHub
    print("\nUploading changes to GitHub...")
    run_git(["push", "-u", "origin", branch])

    print("\n================================")
    print("       SYNC COMPLETED!")
    print("================================")
    print("GitHub has received your changes.")
    print("Vercel will automatically redeploy the website.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        print("\nGit operation failed:")
        print(error.stderr or error.stdout or str(error))
        sys.exit(1)
