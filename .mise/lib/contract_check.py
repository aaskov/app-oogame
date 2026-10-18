"""check:contracts for the backend.

The backend must serve exactly the operations (method + path) in the contract.
This file is guarded (CODEOWNERS), so an agent cannot weaken the check.
It compares operations only. Request and response schemas are not compared yet.

An operation with "x-planned: true" is not built yet. It can be missing. When
the backend serves it, the check prints a note to remove the flag.
"""

import sys
from pathlib import Path
from typing import Any

import yaml

METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}


def operations(spec: dict[str, Any], planned: bool | None = None) -> set[tuple[str, str]]:
    """The (METHOD, path) pairs. planned=True or False selects on x-planned."""
    return {
        (method.upper(), path)
        for path, item in (spec.get("paths") or {}).items()
        for method, operation in item.items()
        if method in METHODS
        and (planned is None or bool((operation or {}).get("x-planned")) == planned)
    }


def main(contract_file: str, backend_dir: str) -> int:
    contract = yaml.safe_load(Path(contract_file).read_text())
    sys.path.insert(0, backend_dir)
    from app.main import create_app

    required = operations(contract, planned=False)
    planned = operations(contract, planned=True)
    served = operations(create_app().openapi())
    for method, path in sorted(required - served):
        print(f"check:contracts: {method} {path} is in the contract, "
              "but the backend does not serve it.", file=sys.stderr)
    for method, path in sorted(served - required - planned):
        print(f"check:contracts: the backend serves {method} {path}, "
              "but it is not in the contract.", file=sys.stderr)
    for method, path in sorted(served & planned):
        print(f"check:contracts: note: {method} {path} is built. "
              "The architect removes its x-planned flag.")
    return 1 if (required - served) or (served - required - planned) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
