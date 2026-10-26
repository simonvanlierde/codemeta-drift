# Task runner: https://just.systems. `just` lists the recipes, `just <name>` runs one.
#
# `import?` skips a recipe file you did not scaffold. Recipes are prefixed
# (`py-`, `ts-`, `rs-`, `go-`) because imports share one namespace.
import? 'just/python.just'
import? 'just/ts.just'
import? 'just/rust.just'
import? 'just/go.just'
import? 'just/docker.just'

# List the recipes (what a bare `just` runs).
default:
    @just --list

# The stack checks CI runs. `just hooks` runs the git hooks, which CI also runs.
check:
    @just py-check

# Run every git hook over the whole repo, not just staged files.
hooks:
    prek run -a

# Mutation-test checks.py with tests/test_checks.py; fails on a survivor not in tests/mutation-baseline.txt.
mutation:
    #!/usr/bin/env bash
    set -euo pipefail
    # mutmut reuses results from mutants/ even after the tests change, so start clean.
    rm -rf mutants
    uv run mutmut run >/dev/null
    survivors=$(uv run mutmut results | sed -n 's/^ *\(.*\): survived$/\1/p' | sort)
    new=$(comm -23 <(echo "$survivors" | sed '/^$/d') <(grep -v '^#' tests/mutation-baseline.txt | awk '{ print $1 }' | sort))
    echo "$(echo "$survivors" | grep -c . || true) survivors; not in tests/mutation-baseline.txt:"
    echo "${new:-none}"
    [ -z "$new" ]
