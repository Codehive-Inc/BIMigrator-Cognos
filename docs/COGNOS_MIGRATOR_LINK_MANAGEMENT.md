# Cognos Migrator Symbolic Link Management

This document outlines procedures for managing the Cognos migrator symbolic link in the MicroStrategy migrator project to prevent unintended changes to the original Cognos migrator codebase.

## Current Setup

The MicroStrategy migrator currently uses a symbolic link to access the Cognos migrator for shared functionality (staging table handlers, models, etc.).

## Procedures

### 1. Adding Cognos Migrator as Symbolic Link

**Prerequisites:**
- Cognos migrator repository exists at: `/Users/sree/Sites/loan-site-AI-lovable/bi-report-migration/BIMigrator-Cognos`
- MicroStrategy migrator project directory: `/Users/sree/Sites/loan-site-AI-lovable/bi-report-migration/BiMigrator-Microstrategy`

**Steps:**

```bash
# Navigate to MicroStrategy migrator directory
cd /Users/sree/Sites/loan-site-AI-lovable/bi-report-migration/BiMigrator-Microstrategy

# Create symbolic link to Cognos migrator
ln -s ../BIMigrator-Cognos/cognos_migrator cognos_migrator

# Verify the link was created
ls -la cognos_migrator
# Should show: cognos_migrator -> ../BIMigrator-Cognos/cognos_migrator

# Test the link works
python -c "import cognos_migrator; print('Link working')"
```

### 1.1. Using Git Submodule (Recommended for Version Control)

**Adding Cognos Migrator as Git Submodule:**

```bash
# Navigate to MicroStrategy migrator directory
cd /Users/sree/Sites/loan-site-AI-lovable/bi-report-migration/BiMigrator-Microstrategy

# Method 1: Add submodule with local path
git submodule add /Users/sree/Sites/loan-site-AI-lovable/bi-report-migration/BIMigrator-Cognos cognos-migrator

# Method 2: Add submodule with relative path (more portable)
git submodule add ../BIMigrator-Cognos cognos-migrator

# Method 3: Add submodule with remote URL (if hosted on Git server)
# git submodule add https://github.com/your-org/BIMigrator-Cognos.git cognos-migrator

# Create flattened symbolic link for easier imports
ln -s cognos-migrator/cognos_migrator cognos_migrator

# Initialize and update submodule
git submodule init
git submodule update

# Verify setup
ls -la cognos-migrator/  # Should show the Cognos migrator files
ls -la cognos_migrator   # Should show symbolic link: cognos_migrator -> cognos-migrator/cognos_migrator

# Test import
python -c "import cognos_migrator; print('Submodule setup successful')"

# Commit the submodule addition
git add .gitmodules cognos-migrator cognos_migrator
git commit -m "Add Cognos migrator as submodule with symbolic link"
```

**Cloning Project with Submodules:**

```bash
# When someone else clones the repository
git clone /path/to/BiMigrator-Microstrategy
cd BiMigrator-Microstrategy

# Initialize and update submodules
git submodule init
git submodule update

# Or clone with submodules in one command
git clone --recursive /path/to/BiMigrator-Microstrategy

# Recreate symbolic link if needed
ln -s cognos-migrator/cognos_migrator cognos_migrator
```

**Updating Submodule to Latest Version:**

```bash
# Navigate to submodule directory
cd cognos-migrator

# Pull latest changes from Cognos migrator
git pull origin main

# Go back to main project
cd ..

# Commit the submodule update
git add cognos-migrator
git commit -m "Update Cognos migrator submodule to latest version"

# Push changes
git push
```

### 2. Removing Cognos Migrator Symbolic Link and Submodule

#### 2.1. Removing Symbolic Link Only (Keep Submodule)

```bash
# Navigate to MicroStrategy migrator directory
cd /Users/sree/Sites/loan-site-AI-lovable/bi-report-migration/BiMigrator-Microstrategy

# Check if it's a symbolic link (safer)
ls -la cognos_migrator
# If it shows "cognos_migrator -> ..." then it's a symbolic link

# Remove the symbolic link (SAFE - only removes the link, not the original)
rm cognos_migrator

# Verify removal
ls -la | grep cognos_migrator
# Should show no cognos_migrator entry (but cognos-migrator submodule remains)

# Commit the change
git add -A
git commit -m "Remove cognos_migrator symbolic link"
```

#### 2.2. Removing Git Submodule Completely

**Method 1: Complete Submodule Removal (Git 1.8.3+)**

```bash
# Navigate to MicroStrategy migrator directory
cd /Users/sree/Sites/loan-site-AI-lovable/bi-report-migration/BiMigrator-Microstrategy

# Remove symbolic link first
rm cognos_migrator

# Remove the submodule (modern Git versions)
git submodule deinit -f cognos-migrator
git rm -f cognos-migrator
rm -rf .git/modules/cognos-migrator

# Clean up .gitmodules file (if no other submodules exist)
# Check if .gitmodules has other entries
cat .gitmodules

# If only cognos-migrator was in .gitmodules, remove the file
rm .gitmodules

# If other submodules exist, manually edit .gitmodules to remove cognos-migrator section
# vim .gitmodules  # Remove the [submodule "cognos-migrator"] section

# Commit the removal
git add -A
git commit -m "Remove Cognos migrator submodule and symbolic link"

# Verify removal
ls -la | grep cognos  # Should show no cognos entries
git submodule status  # Should not show cognos-migrator
```

**Method 2: Manual Submodule Removal (Older Git versions)**

```bash
# Navigate to MicroStrategy migrator directory
cd /Users/sree/Sites/loan-site-AI-lovable/bi-report-migration/BiMigrator-Microstrategy

# Remove symbolic link
rm cognos_migrator

# Deinitialize the submodule
git submodule deinit cognos-migrator

# Remove submodule from git index
git rm cognos-migrator

# Remove submodule directory from .git/modules
rm -rf .git/modules/cognos-migrator

# Edit .gitmodules file to remove the submodule entry
vim .gitmodules
# Remove these lines:
# [submodule "cognos-migrator"]
#     path = cognos-migrator
#     url = /Users/sree/Sites/loan-site-AI-lovable/bi-report-migration/BIMigrator-Cognos

# If .gitmodules is now empty, remove it
# rm .gitmodules

# Edit .git/config to remove submodule entry
vim .git/config
# Remove these lines:
# [submodule "cognos-migrator"]
#     url = /Users/sree/Sites/loan-site-AI-lovable/bi-report-migration/BIMigrator-Cognos

# Commit all changes
git add -A
git commit -m "Completely remove Cognos migrator submodule"

# Verify removal
git submodule status
ls -la | grep cognos
```

#### 2.3. Removing Submodule but Keeping Local Copy

```bash
# Navigate to MicroStrategy migrator directory
cd /Users/sree/Sites/loan-site-AI-lovable/bi-report-migration/BiMigrator-Microstrategy

# Create a backup copy before removal
cp -r cognos-migrator cognos_migrator_backup

# Remove symbolic link
rm cognos_migrator

# Remove submodule
git submodule deinit -f cognos-migrator
git rm -f cognos-migrator
rm -rf .git/modules/cognos-migrator

# Rename backup to regular directory
mv cognos_migrator_backup cognos_migrator

# Add to .gitignore to prevent accidental commits
echo "cognos_migrator/" >> .gitignore

# Commit changes
git add .gitignore
git commit -m "Remove submodule, keep local copy of Cognos migrator"
```

**⚠️ CRITICAL WARNING:**
- **NEVER use `rm -rf cognos_migrator/`** - This could delete the original Cognos migrator files
- **Always use `rm cognos_migrator`** (without trailing slash) to remove only the symbolic link

### 3. Isolation Strategies to Prevent Changes

#### Strategy A: Remove Dependency Completely (Recommended)

Since staging table functionality is now integrated into `bimigrator_mstr`, remove the Cognos dependency:

```bash
# Remove symbolic link
rm cognos_migrator

# Update any remaining imports in code
# Change: from cognos_migrator.* import *
# To: from bimigrator_mstr.* import *

# Remove from .gitignore if present
sed -i '' '/cognos_migrator/d' .gitignore

# Remove from .gitmodules if using submodules
rm .gitmodules
```

#### Strategy B: Read-Only Access

If you need to keep the link for reference:

```bash
# Make the linked directory read-only
chmod -R 444 cognos_migrator/

# Or create a read-only bind mount (Linux/macOS)
sudo mount -o bind,ro /path/to/original/cognos_migrator cognos_migrator
```

#### Strategy C: Copy Instead of Link

Create a static copy instead of a dynamic link:

```bash
# Remove symbolic link
rm cognos_migrator

# Copy the directory (creates independent copy)
cp -r ../BIMigrator-Cognos/cognos_migrator ./cognos_migrator

# Add to .gitignore to prevent accidental commits
echo "cognos_migrator/" >> .gitignore
```

#### Strategy D: Git Worktree (Advanced)

Use git worktree for isolated development:

```bash
# In Cognos migrator repo, create a worktree
cd /Users/sree/Sites/loan-site-AI-lovable/bi-report-migration/BIMigrator-Cognos
git worktree add ../BiMigrator-Microstrategy/cognos_migrator_readonly main

# This creates a read-only checkout that won't affect main development
```

## Verification Commands

### Check Current Setup
```bash
# Check if cognos_migrator exists and its type
ls -la cognos_migrator

# Check if it's a symbolic link
file cognos_migrator

# Check submodule status
git submodule status

# Check .gitmodules content
cat .gitmodules

# Check if imports work
python -c "import sys; sys.path.append('.'); import cognos_migrator; print('Import successful')"
```

### Test Isolation
```bash
# Try to modify a file (should fail if properly isolated)
echo "test" >> cognos_migrator/test_file.txt

# Check git status in both repositories
git status
cd ../BIMigrator-Cognos && git status

# Check submodule git status
cd cognos-migrator && git status && cd ..
```

### Troubleshooting Submodules

#### Issue: Submodule directory is empty
```bash
# Initialize and update submodules
git submodule init
git submodule update

# Or force update
git submodule update --init --recursive --force
```

#### Issue: Submodule shows modified files
```bash
# Check what's modified in submodule
cd cognos-migrator
git status
git diff

# Reset submodule to clean state
git reset --hard HEAD
cd ..

# Update parent repository to track the reset
git add cognos-migrator
git commit -m "Reset submodule to clean state"
```

#### Issue: Cannot remove submodule
```bash
# Force remove if standard removal fails
git rm --cached cognos-migrator
rm -rf cognos-migrator
rm -rf .git/modules/cognos-migrator

# Edit .gitmodules manually
vim .gitmodules

# Edit .git/config manually  
vim .git/config
```

#### Issue: Submodule URL changed
```bash
# Update submodule URL in .gitmodules
vim .gitmodules

# Sync the new URL
git submodule sync

# Update to new URL
git submodule update --init --recursive
```

## Recommended Approach

**For Production/Stable Development:**
- Use **Strategy A** (Remove Dependency) since staging functionality is now integrated
- Keep the MicroStrategy migrator completely independent

**For Active Development/Testing:**
- Use **Strategy C** (Copy Instead of Link) for safety
- Manually sync important updates when needed

**For Reference Only:**
- Use **Strategy B** (Read-Only Access) if you need to reference Cognos code

## Troubleshooting

### Issue: Import errors after removing link
```bash
# Update Python path or imports in code
grep -r "from cognos_migrator" bimigrator_mstr/
# Replace with appropriate bimigrator_mstr imports
```

### Issue: Tests failing after removal
```bash
# Check test dependencies
grep -r "cognos_migrator" tests/
# Update test imports and mocks
```

### Issue: Accidentally modified original Cognos files
```bash
# Check git status in Cognos repo
cd ../BIMigrator-Cognos
git status
git diff

# Revert changes if needed
git checkout -- .
```

## Best Practices

1. **Always verify link type** before removal: `ls -la cognos_migrator`
2. **Use relative paths** for symbolic links to maintain portability
3. **Document dependencies** in requirements.txt or pyproject.toml
4. **Test thoroughly** after any link management operations
5. **Keep backups** of working configurations before major changes
6. **Use version control** to track link management changes
