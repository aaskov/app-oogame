"""check:contracts for the backend.

The backend must serve exactly the operations (method + path) in the contract.
For each built operation, the parameters, the request body, the response codes,
and the response schemas must be equal to the contract (docs/adr/0110).
This file is guarded (CODEOWNERS), so an agent cannot weaken the check.

An operation with "x-planned: true" is not built yet. It can be missing. When
the backend serves it, the check prints a note to remove the flag.

No served operation can declare null, also a planned one (docs/adr/0110). An
optional field uses SkipJsonSchema[None].
"""

import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}

# Text for people, not for the API. The check does not compare these keys.
# "default" is ignored, because Pydantic writes "default: null" for an
# optional field that the client can leave out.
IGNORED_KEYS = {"title", "description", "summary", "tags", "examples", "example", "default"}


def operations(spec: dict[str, Any], planned: bool | None = None) -> set[tuple[str, str]]:
    """The (METHOD, path) pairs. planned=True or False selects on x-planned."""
    return {
        (method.upper(), path)
        for path, item in (spec.get("paths") or {}).items()
        for method, operation in item.items()
        if method in METHODS
        and (planned is None or bool((operation or {}).get("x-planned")) == planned)
    }


def resolve(spec: dict[str, Any], node: Any) -> Any:
    """Replace each $ref with its target, drop the ignored keys, and make 1.0 equal to 1."""
    if isinstance(node, dict):
        if "$ref" in node:
            target: Any = spec
            for part in node["$ref"].removeprefix("#/").split("/"):
                target = target[part]
            return resolve(spec, target)
        return {
            key: resolve(spec, value)
            for key, value in node.items()
            if key not in IGNORED_KEYS and not key.startswith("x-")
        }
    if isinstance(node, list):
        return [resolve(spec, value) for value in node]
    if isinstance(node, float) and node.is_integer():
        return int(node)
    return node


def shape(spec: dict[str, Any], path: str, method: str) -> dict[str, Any]:
    """The parts of one operation that the check compares."""
    item = spec["paths"][path]
    operation = item[method]
    parameters = [resolve(spec, p) for p in item.get("parameters", []) + operation.get("parameters", [])]
    responses: dict[str, Any] = {}
    for code, response in (operation.get("responses") or {}).items():
        content = resolve(spec, response).get("content") or {}
        responses[str(code)] = content.get("application/json", {}).get("schema")
    body = operation.get("requestBody")
    return {
        "parameters": {f"{p['in']}:{p['name']}": p for p in parameters},
        "requestBody": resolve(spec, body) if body else None,
        "responses": responses,
    }


def differences(contract: Any, backend: Any, where: str) -> Iterator[str]:
    if isinstance(contract, dict) and isinstance(backend, dict):
        for key in sorted(set(contract) | set(backend), key=str):
            if key not in backend:
                yield f"{where}/{key}: only in the contract"
            elif key not in contract:
                yield f"{where}/{key}: only in the backend"
            else:
                yield from differences(contract[key], backend[key], f"{where}/{key}")
    elif contract != backend:
        yield f"{where}: the contract has {json.dumps(contract)}, the backend has {json.dumps(backend)}"


def nulls(node: Any, where: str) -> Iterator[str]:
    """The places where a schema allows null."""
    if isinstance(node, dict):
        kind = node.get("type")
        if kind == "null" or (isinstance(kind, list) and "null" in kind):
            yield where
        for key, value in node.items():
            yield from nulls(value, f"{where}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from nulls(value, f"{where}/{index}")


def main(contract_file: str, backend_dir: str) -> int:
    contract = yaml.safe_load(Path(contract_file).read_text())
    sys.path.insert(0, backend_dir)
    from app.main import create_app

    backend = create_app().openapi()
    required = operations(contract, planned=False)
    planned = operations(contract, planned=True)
    served = operations(backend)
    for method, path in sorted(required - served):
        print(f"check:contracts: {method} {path} is in the contract, "
              "but the backend does not serve it.", file=sys.stderr)
    for method, path in sorted(served - required - planned):
        print(f"check:contracts: the backend serves {method} {path}, "
              "but it is not in the contract.", file=sys.stderr)
    for method, path in sorted(served & planned):
        print(f"check:contracts: note: {method} {path} is built. "
              "The architect removes its x-planned flag.")

    mismatches = [
        line
        for method, path in sorted(served & required)
        for line in differences(
            shape(contract, path, method.lower()),
            shape(backend, path, method.lower()),
            f"{method} {path}",
        )
    ]
    mismatches += [
        f"{where}: the backend allows null. Use SkipJsonSchema[None] (docs/adr/0110)."
        for method, path in sorted(served)
        for where in nulls(shape(backend, path, method.lower()), f"{method} {path}")
    ]
    for line in mismatches:
        print(f"check:contracts: {line}", file=sys.stderr)
    if mismatches:
        print("check:contracts: make the backend schemas match the contract (docs/adr/0110).",
              file=sys.stderr)
    return 1 if (required - served) or (served - required - planned) or mismatches else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
