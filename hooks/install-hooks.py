# hooks/install_hooks.py
import os
import shutil
import stat

def make_executable(path):
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC)

def install_hooks():
    git_hooks_dir = os.path.join(".git", "hooks")
    if not os.path.exists(git_hooks_dir):
        print("Error: Not a Git repository")
        return

    hooks_source = "hooks/pre-commit"
    hooks_dest = os.path.join(git_hooks_dir, "pre-commit")

    shutil.copy(hooks_source, hooks_dest)
    make_executable(hooks_dest)
    print("Git hooks installed successfully!")

if __name__ == "__main__":
    install_hooks()
