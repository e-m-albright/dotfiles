# Clearing history of a git repository
Useful to wipe the project history

# Ensure you're in your repository directory
cd your-repository

# Create a new branch without any history
git checkout --orphan temp_branch

# Add all files to the new branch
git add -A

# Create a new commit with all files
git commit -m "Initial commit: Complete repository reset"

# Delete the main branch
git branch -D main

# Rename temp branch to main
git branch -m main

# Force push to remote repository
git push -f origin main

# Optional: Remove old refs and garbage collect
git for-each-ref --format="%(refname)" refs/original/ | xargs -n 1 git 
update-ref -d
git reflog expire --expire=now --all
git gc --aggressive --prune=now

# Note: Other developers will need to:
# 1. Remove their local repository: rm -rf your-repository
# 2. Clone fresh: git clone <repository-url>
# OR
# 1. git fetch origin
# 2. git reset --hard origin/main
