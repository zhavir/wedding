"""Exercise GitHub synchronization against a local fake CLI, never GitHub."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def github_cli(tmp_path):
    if not shutil.which("jq"):
        pytest.skip("The shell synchronization tests require jq")
    checkout = tmp_path / "checkout"
    shutil.copytree(ROOT / ".github/rulesets", checkout / ".github/rulesets")
    state = tmp_path / "state.json"
    state.write_text(
        json.dumps({
            "rules": [{"id": 90, "name": "Restrict default branch updates administrators"}],
            "calls": [],
        })
    )
    executable = tmp_path / "gh"
    executable.write_text("""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
path = Path(os.environ["FAKE_GH_STATE"])
state = json.loads(path.read_text())
args = sys.argv[1:]
method = args[args.index("--method") + 1] if "--method" in args else "GET"
endpoint = next(item for item in args if item.startswith("repos/"))
if method == "GET":
    print(json.dumps([state["rules"]] if "--paginate" in args else {"permissions": {"admin": os.environ.get("FAKE_ADMIN", "1") == "1"}}))
    sys.exit(0)
payload = json.loads(Path(args[args.index("--input") + 1]).read_text()) if "--input" in args else None
state["calls"].append({"method": method, "endpoint": endpoint, "payload": payload})
path.write_text(json.dumps(state))
if os.environ.get("FAKE_FAIL") == method:
    sys.exit(1)
if method == "POST":
    state["rules"].append({"id": len(state["rules"]) + 100, "name": payload["name"]})
elif method == "DELETE":
    state["rules"] = [rule for rule in state["rules"] if str(rule["id"]) != endpoint.split("/")[-1]]
path.write_text(json.dumps(state))
print("{}")
""")
    executable.chmod(0o700)
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "FAKE_GH_STATE": str(state),
        "GH_TOKEN": "synthetic-local-test-token",
        "RELEASE_APP_ID": "12345",
        "GITHUB_REPOSITORY": "owner/wedding",
    }

    def run(**overrides):
        result = subprocess.run(
            ["bash", str(ROOT / "scripts/sync_rulesets.sh")],
            cwd=checkout,
            env=env | overrides,
            capture_output=True,
            text=True,
            check=False,
        )
        assert env["GH_TOKEN"] not in result.stdout + result.stderr
        return result, json.loads(state.read_text())

    return run


def test_ruleset_sync_is_idempotent_and_retires_only_after_success(github_cli):
    result, state = github_cli()
    assert result.returncode == 0, result.stderr
    assert [call["method"] for call in state["calls"]] == ["POST", "POST", "DELETE"]
    for call in state["calls"][:2]:
        actors = call["payload"]["bypass_actors"]
        assert (
            next(actor["actor_id"] for actor in actors if actor["actor_type"] == "Integration")
            == 12345
        )
    result, state = github_cli()
    assert result.returncode == 0, result.stderr
    assert [call["method"] for call in state["calls"][-2:]] == ["PUT", "PUT"]
    assert len(state["rules"]) == 2


@pytest.mark.parametrize(
    "overrides", [{"FAKE_ADMIN": "0"}, {"RELEASE_APP_ID": "0"}, {"GH_TOKEN": ""}]
)
def test_ruleset_sync_rejects_invalid_authorization_before_writes(github_cli, overrides):
    result, state = github_cli(**overrides)
    assert result.returncode != 0
    assert state["calls"] == []


def test_ruleset_sync_keeps_retired_rule_when_api_fails(github_cli):
    result, state = github_cli(FAKE_FAIL="POST")
    assert result.returncode != 0
    assert not any(call["method"] == "DELETE" for call in state["calls"])
    assert state["rules"][0]["id"] == 90
