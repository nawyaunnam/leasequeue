# Engineering notes: LeaseQueue — durable background jobs

## Problem and flow

Producer → unique idempotency key → SQLite queue → atomic worker claim → lease token → acknowledge or retry. A worker must present its current token before modifying a running job. `BEGIN IMMEDIATE` serializes claims across connections; expired leases can be reclaimed.

## Current boundaries

Single-host SQLite, at-least-once delivery. Handlers must make side effects idempotent. No external broker, distributed clock agreement, or background polling daemon. Exhausted jobs are retained for inspection.

## Interview walkthrough

1. Run the demo and explain each output in terms of the code.
2. Show a test that exercises a failure rather than only a successful call.
3. Trace one input through the core implementation and its stored state.
4. Explain the tradeoff made by the current storage or algorithm choice.
5. Describe what would change with 100× the data or concurrent users.
6. Make a small extension and add a regression test before using this in a resume.

## Validation

See `test_engine.py` for executable assertions and `docs/demo-output.txt` for
captured results. CI is configured but remote CI results are not assumed.
