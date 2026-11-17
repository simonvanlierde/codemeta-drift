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

# Run at the end of `just check`.
local-check:
    @node --test site/*.test.mjs

# Render the social card, site/og.png, from docs/og-card.html (needs Node and a Playwright Chromium).
# Then put the PNG's hash in the og:image URL: link previews are cached by image URL.
og-card:
    pnpm dlx playwright@1.64.1 screenshot --browser=chromium --viewport-size=1200,630 \
      "file://$PWD/docs/og-card.html" site/og.png
    sed -E -i.bak "s/og\.png(\?v=[0-9a-f]+)?\"/og.png?v=$(shasum -a 256 site/og.png | cut -c1-8)\"/" site/index.html
    rm site/index.html.bak

# Mutation-test the modules in pyproject's [tool.mutmut]. Fails on a survivor not in
# tests/mutation-baseline.txt, and on a listed one that no longer survives, so the list stays true.
mutation:
    #!/usr/bin/env bash
    set -euo pipefail
    # sort and comm must agree on the ǁ in class-method mutant names, so use byte order.
    export LC_ALL=C
    # mutmut reuses results from mutants/ even after the tests change, so start clean.
    rm -rf mutants
    uv run mutmut run >/dev/null
    survivors=$(uv run mutmut results | sed -n 's/^ *\(.*\): survived$/\1/p' | sort)
    listed=$(grep -v '^#' tests/mutation-baseline.txt | awk '{ print $1 }' | sort)
    new=$(comm -23 <(echo "$survivors" | sed '/^$/d') <(echo "$listed"))
    gone=$(comm -13 <(echo "$survivors") <(echo "$listed" | sed '/^$/d'))
    echo "$(echo "$survivors" | grep -c . || true) survivors; not in tests/mutation-baseline.txt:"
    echo "${new:-none}"
    echo "listed but no longer surviving (drop them):"
    echo "${gone:-none}"
    [ -z "$new$gone" ]

# Write each tag's SSSOM export to a temp file and validate it with the pinned reference tool (needs network for uvx).
sssom-validate:
    #!/usr/bin/env bash
    set -euo pipefail
    out=$(mktemp -d)
    trap 'rm -rf "$out"' EXIT
    for mapping in examples/mapping-*.json; do
        uv run codemeta-drift hub sssom "$mapping" --out "$out/spokes.sssom.tsv"
        uvx --python 3.13 --from sssom==0.4.21 sssom validate "$out/spokes.sssom.tsv"
    done
