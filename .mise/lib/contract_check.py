"""check:contracts for the backend.

The backend must serve exactly the operations (method + path) in the contract.
This file is guarded (CODEOWNERS), so an agent cannot weaken the check.
It compares operations only. Request and response schemas are not compared yet.
"""

import sys
from pathlib import Path
from typing import Any

import yaml

METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}


def operations(spec: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, item in (spec.get("paths") or {}).items()
        for method in item
        if method in METHODS
    }


def main(contract_file: str, backend_dir: str) -> int:
    contract = yaml.safe_load(Path(contract_file).read_text())
    sys.path.insert(0, backend_dir)
    from app.main import create_app

    wanted = operations(contract)
    served = operations(create_app().openapi())
    for method, path in sorted(wanted - served):
        print(f"check:contracts: {method} {path} is in the contract, "
              "but the backend does not serve it.", file=sys.stderr)
    for method, path in sorted(served - wanted):
        print(f"check:contracts: the backend serves {method} {path}, "
              "but it is not in the contract.", file=sys.stderr)
    return 1 if wanted != served else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
