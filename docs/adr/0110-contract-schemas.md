# 0110 — check:contracts compares the schemas, not only the operations

**Status:** Accepted · 2026-10-19

## Context

`check:contracts` compared only the operations (method + path). In the planets
feature, `PATCH /planets/{planet_id}/vault` accepted `{"metal": null}`, but the
contract allows only an integer. The gate did not see it (issue #28). A first
comparison found four more gaps of the same kind.

## Decision

- For each built operation, the check compares the contract with the schema
  that FastAPI generates: the parameters, the request body, the response
  codes, and each JSON response schema. They must be **equal**.
- Before it compares, the check:
  - resolves each `$ref`, so the schema names do not matter (`User`, `UserOut`);
  - ignores text for people: `title`, `description`, `summary`, `tags`,
    `examples`, `example`, and keys that start with `x-`;
  - ignores `default`, because Pydantic writes `default: null` for an optional field;
  - makes `1.0` equal to `1`.
- Each difference prints one line with its location, for example
  `PATCH /planets/{planet_id}/vault/requestBody/.../metal/anyOf: only in the backend`.
- A field that a client can leave out, but cannot send as null, is
  `Amount | SkipJsonSchema[None] = None` with a validator that refuses `None`.
- A 422 answer in the contract has no body. A router declares it as `422: {}`.
  Then FastAPI does not publish its own error body.

## Consequences

- The contract and the backend must agree on each constraint, in both directions.
- The check does not run the app. It compares what the app says that it does.
  A bug inside a handler is still a job for the tests.
- The frontend types still come from the contract. They are not compared with the backend.
