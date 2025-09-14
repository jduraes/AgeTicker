#!/bin/bash

# Bump version script for AgeTicker
# Usage: ./scripts/bump-version.sh [patch|minor|major] [message]

set -e

# Default to patch bump if no argument provided
BUMP_TYPE=${1:-patch}
COMMIT_MESSAGE=${2:-"Version bump"}

# Get current version from main.py
CURRENT_VERSION=$(grep '^VERSION = ' main.py | sed 's/VERSION = "\(.*\)"/\1/')
echo "Current version: $CURRENT_VERSION"

# Parse version components
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Bump version based on type
case $BUMP_TYPE in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
    *)
        echo "Usage: $0 [patch|minor|major] [commit_message]"
        echo "Example: $0 minor 'Added new feature'"
        exit 1
        ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"
echo "New version: $NEW_VERSION"

# Confirm the change
read -p "Bump version from $CURRENT_VERSION to $NEW_VERSION? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Update version in main.py
sed -i.bak "s/VERSION = \"$CURRENT_VERSION\"/VERSION = \"$NEW_VERSION\"/" main.py
rm main.py.bak

# Commit the version change
git add main.py
git commit -m "$COMMIT_MESSAGE to v$NEW_VERSION"

# Create and push tag
git tag "v$NEW_VERSION"
git push origin master
git push origin "v$NEW_VERSION"

echo "✅ Version bumped to v$NEW_VERSION"
echo "🚀 Release workflow should be triggered automatically"
echo "📦 Check GitHub Actions: https://github.com/$(git config remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"