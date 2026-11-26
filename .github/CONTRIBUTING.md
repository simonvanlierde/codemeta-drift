# Contributing

Read the [Code of Conduct](CODE_OF_CONDUCT.md) first. Report vulnerabilities as
[SECURITY.md](SECURITY.md) describes, not in a public issue.

## Report a bug or ask for a feature

Open an [issue](https://github.com/simonvanlierde/codemeta-drift/issues) with the bug or
feature form. For a bug, say what you did, what you expected and what happened, with the
release or commit you used. A question the README and docs don't answer is a docs gap: open a
feature request for it.

## Scope and response

One person maintains codemeta-drift, in their own time. Expect a reply to an issue or
pull request within about two weeks.

For a large pull request, such as a new feature or a change to how something works, open an
issue and agree on the change there first. A small fix needs no issue. A pull request outside
the project's scope is closed with a link to this section.

## Set up and check

The [README](../README.md) says how to install the tools, the dependencies and the git hooks.
`just check` runs the checks CI runs. `just fmt` fixes and formats.

uv locks only releases at least a week old. If `just check` fails on a newer security fix,
add the package to `exclude-newer-package` under `[tool.uv]` in `pyproject.toml`, and remove
it a week later ([how](https://github.com/simonvanlierde/project-templates/blob/main/docs/tooling.md#dependencies)).

## Write commits and pull requests

- **Commits** follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):
  `type(scope): summary`, in the imperative, lower case, with no period. Add a body only
  when the change needs one, with a bullet per logical chunk.
- **The pull request title** becomes the squash commit subject and follows the same rule.
- **Both are checked** against [`committed.toml`](../committed.toml). A commit-msg hook
  (installed by `prek install`) refuses a commit message that breaks the rule, and the
  `pull request title` check fails a pull request whose title does. Lower case isn't checked.
  Title a revert `revert: <original subject>`: rename the `Revert "..."` title that GitHub's
  Revert button writes.
- **The pull request body** has the shape of
  [the pull request template](pull_request_template.md): what it fixes and why, three or
  four bullets, a `Tested:` line with the proof (the command and its result, or a test
  that fails without the change), and a `Not checked:` line with what did not run and why,
  plus any design choice or security path that only a person can judge. "Nothing" is fine.
- **The changelog** ([CHANGELOG.md](../CHANGELOG.md)) follows
  [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/). Write each entry for
  the project's users, not as a commit subject. Mark breaking changes
  **Breaking**, and put upgrade steps first under the version.
- **The release notes** are that version's changelog section.

## Make a release

The maintainer runs `just release X.Y.Z`. [Publishing](https://github.com/simonvanlierde/project-templates/blob/main/docs/setup.md#publishing) has the steps and the one-time setup.

## Sign off your commits

Every commit in a pull request carries a `Signed-off-by:` line. It says you wrote the change
or have the right to submit it under this project's license, as the
[Developer Certificate of Origin 1.1](https://developercertificate.org/) defines. `git commit -s`
adds the line, and the commit-msg hook refuses a commit without it.

To add it to commits you already made, run `git fetch origin`, then
`git rebase --signoff origin/main`. In a fork, use the remote that points at this repository (often `upstream`) in place of
`origin`. If you already pushed the branch, update it with `git push --force-with-lease`, never
a plain `git push --force`.

The `dco` workflow fails a fork pull request that has a commit without a sign-off. Pull
requests from this repository skip that check, but every commit still needs a sign-off.

## Who maintains this

Simon van Lierde ([simonvanlierde](https://github.com/simonvanlierde) on GitHub) reviews and
merges pull requests and makes releases. Only maintainers can merge to `main`. An existing
maintainer adds a new maintainer by name in this section. If no maintainer can continue, the
repository is archived with a note in the README.
