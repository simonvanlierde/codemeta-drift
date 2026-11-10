# Recipes for this repo alone; the rest of the justfile comes from the project template.

# No reviewers, so the unattended Monday run is never held. The secret itself goes in by hand.
# Create the schema-watch environment for the watcher's token: deployments from main only. Safe to rerun.
watch-env:
    #!/usr/bin/env bash
    set -euo pipefail
    gh api -X PUT "repos/{owner}/{repo}/environments/schema-watch" \
        -F "deployment_branch_policy[protected_branches]=false" \
        -F "deployment_branch_policy[custom_branch_policies]=true" >/dev/null
    policies=$(gh api "repos/{owner}/{repo}/environments/schema-watch/deployment-branch-policies" --jq '.branch_policies[].name')
    if ! grep -qxF main <<<"$policies"; then
        gh api -X POST "repos/{owner}/{repo}/environments/schema-watch/deployment-branch-policies" -f name=main -f type=branch >/dev/null
    fi
    echo "Configured environment 'schema-watch'. Add the secret: gh secret set MAPPING_WATCH_TOKEN --env schema-watch"
