#!/bin/bash

# Path to the folder to remove
FOLDER_PATH="examples/packages/FM Models"

# Store the current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Current branch: $CURRENT_BRANCH"

# Get all branches (local and remote)
BRANCHES=$(git branch -a | grep -v HEAD | sed -e 's/^\s*//' -e 's/^remotes\/origin\///')

# Remove duplicates (local branches that also exist as remote branches)
UNIQUE_BRANCHES=$(echo "$BRANCHES" | sort -u)

echo "Will process the following branches:"
echo "$UNIQUE_BRANCHES"
echo ""

# Ask for confirmation
read -p "This will remove '$FOLDER_PATH' from all branches. Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Operation canceled."
    exit 1
fi

# Process each branch
for BRANCH in $UNIQUE_BRANCHES; do
    # Skip remote branches that don't have local counterparts
    if [[ $BRANCH == origin/* ]]; then
        continue
    fi
    
    echo "Processing branch: $BRANCH"
    
    # Checkout the branch
    git checkout $BRANCH
    
    # Check if the folder exists in this branch
    if [ -d "$FOLDER_PATH" ]; then
        echo "Removing folder from branch: $BRANCH"
        
        # Remove the folder
        rm -rf "$FOLDER_PATH"
        
        # Commit the change
        git add -A
        git commit -m "Remove '$FOLDER_PATH' folder"
        
        # Push the change
        echo "Pushing changes to origin/$BRANCH"
        git push origin $BRANCH
    else
        echo "Folder '$FOLDER_PATH' does not exist in branch: $BRANCH"
    fi
done

# Return to the original branch
echo "Returning to original branch: $CURRENT_BRANCH"
git checkout $CURRENT_BRANCH

echo "Operation completed."
