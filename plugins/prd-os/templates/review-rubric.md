# PRD review rubric

Codex consumes this rubric alongside the target PRD and returns review output.
That output is normalized into JSONL findings conforming to
`plugins/prd-os/schemas/findings.schema.json` by the plugin (never by trusting
Codex output shape directly).

## Dimensions to evaluate

1. **Problem clarity**
   - Is the problem concrete and observed, not aspirational?
   - Is success measurable?

2. **Scope discipline**
   - Do the goals and non-goals draw a clean line?
   - Any scope creep hidden in "proposed approach"?

3. **Atomic decomposition**
   - Does the `## Issues` manifest split work into independently verifiable units?
   - Does every issue name `allowed_files` and at least one `required_check`?
   - Any two issues overlap on `allowed_files`? (Serialization risk.)

4. **Risk surface**
   - Blast radius, migration/rollback, hidden coupling to production systems.
   - Portability: does this change assume a specific repo layout?

5. **Dependencies**
   - Upstream blockers (tools, access, data not yet available).
   - Downstream impact (other teams, other services, config contracts).

6. **Recurring gap classes**
   - For each class below, ask: does this PRD's design account for it, or does
     the change's blast radius touch it without saying how? Flag the in-scope
     ones as `major` (design gap) or `minor` (note it). These are shapes that
     repeatedly ship past review; `gap-classes.md` has the full list with the
     rule and the catch for each.
   - Scaling/persistence: an append-only store without compaction + a bounded
     read in the same change; per-item enrichment before the filter; a breaking
     response-shape change instead of additive params/header; a persistence
     feature whose data path is not verified on a durable mount.
   - Security: a view/UI hide treated as access control (state not enforced at
     the action endpoint on every reachable path); one helper used for both a
     gate (must fail closed) and a filter (may fail open); redaction at a
     mid-pipeline boundary that later code augments past; persisting the raw
     object instead of a redacted projection; masking by appearance instead of
     by recipient+necessity; hiding a thing that buries an open obligation.
   - Correctness/concurrency: a new flag/field that does not reach every reader
     of the store; an overloaded field that changes meaning for existing
     consumers; check-then-mutate on shared state without one lock (+ an
     N-thread reproducer); a health endpoint that can 500 on one bad row; a
     version/identity hardcoded in more than one place.
   - Cross-cutting: an invariant that must hold "everywhere" with no written
     scope (what it does and does NOT cover) and no guard test that enumerates
     its targets from the system rather than a hand list.

## Severity rubric

Assign severity through one lens: **what is the penalty for being wrong?** Weigh
the cost if this concern is real and ships unaddressed against how plausible it
is. High penalty + plausible escalates; low penalty stays a nit regardless of
how certain you are.

- `blocker` — high penalty for being wrong (data loss, security, a broken gate,
  an untestable contract) and plausible. Must fix before the PRD can advance to
  `approved`.
- `major` — significant penalty; approval requires an explicit disposition
  (accepted with fix, rejected with rationale, or deferred with owner).
- `minor` — low penalty for being wrong; worth fixing, not blocking.
- `nit` — effectively no penalty: wording, formatting, non-substantive.

## Adversarial pass

When invoked adversarially (source=`codex-adversarial`), additionally stress-test:
- Failure modes the author didn't consider.
- Assumptions the approach depends on but doesn't state.
- Prior art that already solves this — why build new?
