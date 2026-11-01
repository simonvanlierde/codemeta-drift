"""Poll public schema sources; publish deduplicated issue drafts only with an explicit flag."""

import argparse
import base64
import hashlib
import json
import re
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen

from codemeta_drift.export import curated_tags
from codemeta_drift.watcher import issue_plans, schema_changes

API = "https://api.github.com/repos/"
SCHEMA_URLS = {
    "pep621": "https://json.schemastore.org/pyproject.json",
    "npm": "https://json.schemastore.org/package.json",
    "cargo": "https://json.schemastore.org/cargo.json",
}


def fetch_json(url: str) -> Any:  # noqa: ANN401
    """Read a public HTTPS document with a timeout; never attach credentials."""
    if not url.startswith("https://"):
        msg = "schema and API sources must use HTTPS"
        raise ValueError(msg)
    with urlopen(url, timeout=30) as response:  # noqa: S310 - HTTPS checked above
        return json.load(response)


def stale_pin_hashes(source: str, tag: str, fetch: Callable[[str], Any]) -> list[dict[str, str]]:
    """Draft one citesync issue per `sha256 <hex> <local> <path>` line that differs from the file at the tag."""
    plans = []
    for line in source.splitlines():
        if not line.startswith("sha256 "):
            continue
        _, digest, local, path = line.split()
        published = fetch(API + f"simonvanlierde/codemeta-drift/contents/{path}?ref={quote(tag, safe='')}")
        current = hashlib.sha256(base64.b64decode(published["content"])).hexdigest()
        if current != digest:
            plans.append(
                {
                    "repo": "simonvanlierde/citesync",
                    "title": f"Update mapping pin hash for {local} at {tag}",
                    "body": f"The sha256 of `{local}` in MAPPING_SOURCE is `{digest}`, but `{path}` at "
                    f"{tag} hashes to `{current}`. Re-vendor the file and fix that line.",
                }
            )
    return plans


def poll(
    mapping: dict[str, Any], before: dict[str, Any], fetch: Callable[[str], Any] = fetch_json
) -> list[dict[str, str]]:
    """Build drafts from current public schemas, release tags, and citesync's pin."""
    cff_tag = fetch(API + "citation-file-format/citation-file-format/releases/latest")["tag_name"]
    after = {fmt: fetch(url) for fmt, url in SCHEMA_URLS.items()}
    after["cff-1.2.0"] = fetch(
        "https://raw.githubusercontent.com/citation-file-format/citation-file-format/"
        f"{quote(cff_tag, safe='')}/schema.json"
    )
    after["zenodo"] = before["zenodo"]
    latest = fetch(API + "simonvanlierde/codemeta-drift/releases/latest")["tag_name"]
    pin = fetch(API + "simonvanlierde/citesync/contents/src/citesync/MAPPING_SOURCE")
    # The contents endpoint returns base64 so every source still uses the same JSON fetch contract.
    source = base64.b64decode(pin["content"], validate=False).decode("utf-8")
    pin_tags = [line.split()[1] for line in source.splitlines() if line.startswith("tag ")]
    if len(pin_tags) != 1:
        msg = "citesync MAPPING_SOURCE must have exactly one tag"
        raise ValueError(msg)
    plans = issue_plans(schema_changes(mapping["rows"], before, after), pin_tags[0], latest, set())
    plans += stale_pin_hashes(source, pin_tags[0], fetch)
    # Zenodo has no current public JSON Schema: source changes need a fresh manual path review.
    source = before["zenodo"]["x-source"]
    for path, digest in sorted(source["files"].items()):
        try:
            current_sha = fetch(API + source["repo"] + "/contents/" + path)["sha"]
        except HTTPError as err:
            if err.code != 404:
                raise
            current_sha = "missing"
        if current_sha != digest:
            plans.append(
                {
                    "repo": "simonvanlierde/codemeta-drift",
                    "title": f"Review Zenodo importer {path} {current_sha}",
                    "body": f"`{path}` changed from blob `{digest}` to `{current_sha}`. "
                    "Review the Zenodo structural subset before refreshing its source hashes. "
                    "A source change does not automatically change the mapping.",
                }
            )
    tags = [tag["name"] for tag in fetch(API + "codemeta/codemeta/tags?per_page=100")]
    stable = [tag for tag in tags if re.fullmatch(r"v?[0-9]+(?:\.[0-9]+){1,2}", tag)]
    if stable:
        name = max(stable, key=lambda tag: tuple(map(int, tag.removeprefix("v").split("."))))
        if name not in curated_tags():
            plans.append(
                {
                    "repo": "simonvanlierde/codemeta-drift",
                    "title": f"Review CodeMeta tag {name}",
                    "body": f"CodeMeta tag `{name}` has no curated export. Review its terms and crosswalks.",
                }
            )
    return plans


def publish(
    plans: list[dict[str, str]], titles: Callable[[str], set[str]], create: Callable[[dict[str, str]], None]
) -> None:
    """Fetch all issue titles before publishing, including closed ones; callers serialize runs."""
    existing = {repo: titles(repo) for repo in sorted({plan["repo"] for plan in plans})}
    for plan in plans:
        if plan["title"] not in existing[plan["repo"]]:
            create(plan)
            existing[plan["repo"]].add(plan["title"])


def main() -> None:
    """Poll using the tracked snapshots and export, writing drafts or explicitly publishing them."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(), help="codemeta-drift checkout")
    parser.add_argument("--out", type=Path, required=True, help="JSON draft artifact")
    parser.add_argument("--publish", action="store_true", help="open missing issues using gh's credentials")
    args = parser.parse_args()
    from codemeta_drift.conformance import SCHEMA_FILES  # noqa: PLC0415 - CLI snapshot loading

    mapping = json.loads((args.root / "examples/mapping-3.1.json").read_text("utf-8"))
    before = {
        fmt: json.loads((args.root / "tests/fixtures/schemas" / name).read_text("utf-8"))
        for fmt, name in SCHEMA_FILES.items()
    }
    plans = poll(mapping, before)
    args.out.write_text(json.dumps(plans, indent=2) + "\n", encoding="utf-8")
    if args.publish:
        subprocess.run(["gh", "api", "rate_limit"], check=True, capture_output=True, timeout=30)  # noqa: S607

        def titles(repo: str) -> set[str]:
            output = subprocess.run(  # noqa: S603 - fixed gh operation, no shell
                ["gh", "api", "--paginate", "--slurp", f"repos/{repo}/issues?state=all&per_page=100"],  # noqa: S607
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
            return {issue["title"] for page in json.loads(output) for issue in page}

        def create(plan: dict[str, str]) -> None:
            time.sleep(1)
            subprocess.run(  # noqa: S603 - fixed gh operation, no shell
                [  # noqa: S607 - fixed gh operation, no shell
                    "gh",
                    "issue",
                    "create",
                    "--repo",
                    plan["repo"],
                    "--title",
                    plan["title"],
                    "--body",
                    plan["body"],
                ],
                check=True,
                timeout=30,
            )

        publish(plans, titles, create)


if __name__ == "__main__":
    main()
