#!/usr/bin/env python3
"""Validate VKS add-on values before pushing.

    scripts/check-addon-values.py supervisor/se-ns-argo/se-cluster-01-addons/*/*.yaml

`kubectl apply --dry-run=server` does NOT check AddonConfig values: VKS
validates them later, asynchronously, and a typo only shows up as a failed
AddonConfig after the push. This checks each AddonConfig's spec.values against
the AddonConfigDefinition of the release its AddonInstall pins, and treats
unknown keys as errors (the schemas do not, so typos would otherwise pass).

Needs kubectl access to the Supervisor (KUBE_CONTEXT, default 172.17.10.2).
"""
import json
import os
import subprocess
import sys

import jsonschema
import yaml

CONTEXT = os.environ.get("KUBE_CONTEXT", "172.17.10.2")
ACD_NS = "vmware-system-vks-public"


def kubectl_json(*args):
    out = subprocess.run(["kubectl", "--context", CONTEXT, *args, "-o", "json"],
                         check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def strict(schema):
    """Reject unknown keys wherever a schema lists its properties."""
    if isinstance(schema, dict):
        if "properties" in schema and "additionalProperties" not in schema:
            schema["additionalProperties"] = False
        for v in schema.values():
            strict(v)
    elif isinstance(schema, list):
        for v in schema:
            strict(v)
    return schema


def main(paths):
    acds = {a["metadata"]["name"].replace("---", "-"): a
            for a in kubectl_json("-n", ACD_NS, "get", "addonconfigdefinitions")["items"]}
    failed = False
    for path in paths:
        docs = [d for d in yaml.safe_load_all(open(path)) if d]
        configs = {d["metadata"]["name"]: d for d in docs if d["kind"] == "AddonConfig"}
        for inst in (d for d in docs if d["kind"] == "AddonInstall"):
            release = inst["spec"]["releaseFilter"]["ref"]["name"]
            cfg = configs.get(inst["spec"].get("addonConfigNameTemplate", ""))
            acd = acds.get(release)
            if acd is None:
                print(f"FAIL {path}: no AddonConfigDefinition for release {release}")
                failed = True
                continue
            if cfg is None:
                print(f"ok   {path}: {release} (no AddonConfig, defaults)")
                continue
            spec = acd["spec"]
            schema = strict(spec.get("schema", {}).get("openAPIV3Schema") or spec.get("schema") or {})
            errors = sorted(jsonschema.Draft7Validator(schema).iter_errors(cfg["spec"].get("values", {})),
                            key=lambda e: list(e.path))
            if errors:
                failed = True
                for e in errors:
                    where = ".".join(str(p) for p in e.path) or "values"
                    print(f"FAIL {path}: {where}: {e.message}")
            else:
                print(f"ok   {path}: values valid for {release}")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1:]))
