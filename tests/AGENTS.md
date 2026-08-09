# Test Engineering Principles — Facktry

> **Append-only.** Add new entries below under `## Appended Notes`. Do not edit prior sections unless fixing factual errors.

---

## How do I become a better programmer?

Answered by observing what broke first, and what held up.

### Source of truth means something specific — name the thing
"X is the source of truth" only makes sense if X names one kind of data. A database that stores both bytes AND their metadata has two separate truths in one place — and when one changes, you have no clean signal. Distinguish: where do bytes live versus where do facts about those bytes live. If tampering detection requires touching the bytes themselves, put them somewhere tamperable. Index elsewhere.

### Specifications describe the world as it should be. Tests describe the world as it is.
When these disagree, resolving the tension is the engineering act — not making one conform silently to the other. Understanding *why* each side says what it says turns a merge conflict into an architectural decision with reasoning attached.

### Purity is relative to your boundary.
A function that looks "pure" inside its arguments may depend on state outside them (a database, a catalog, the filesystem). Accepting optional context (`store=None`) preserves purity for callers who don't have it while enabling fullness for those who do. Splitting into two APIs adds surface area without adding substance.

### Symmetry is correctness made structural.
Whatever transformation runs during save MUST run identically during load — same fields stripped, same encoding, same hashing order. Mismatches here don't cause immediate crashes; they produce intermittent failures that look like bugs in unrelated code. Enforce symmetry by design, not by hoping the two paths stay in sync.

### Skip the unprovable test; don't weaken the rule.
When a test asserts behavior that requires infrastructure not yet built, the test is aspirational. Skipping it with an explicit reason preserves the validation logic intact while acknowledging honest incompleteness. Relaxing production rules to appease early-phase tests is how incorrect behavior becomes permanent.

### Placeholder values create invisible debt.
`"a" * 64` looks like a valid SHA-256 hash. It passes type checks. It survives serialization. Then three modules later something verifies the real content against it and nothing matches — and nobody knows whether the hash was wrong, the content was modified, or the comparison is flawed. Recompute hashes at write time. Trust nothing declared upfront.

### You can't rebuild authority from fragments.
Deleting the canonical index then expecting queries to return results presumes that scattered filesystem copies reconstruct the original intent. They don't. If there is one authoritative store, and you destroy it, the system cannot magically reassemble itself from partial derivatives. Design recovery around what is actually recoverable.

### Threading beats multiprocessing when threads share memory.
If concurrent processes can't pickle closures (Python 3.14+ forkserver), and all threads access the same environment anyway, use threads. Independent connections to the same WAL-mode database give you the concurrent-read/write coverage you needed without the serialization headache. Don't reach for heavier concurrency primitives than the problem demands.

### Test behavior, not mechanics.
Mocking `os.replace` to simulate failure only proves value while the implementation uses `os.replace`. When it shifts away, the mock becomes dead weight — asserting a property that no longer maps to anything real. Remove such tests. Keep ones that assert observable contracts regardless of internals.

### Round-trip consistency trumps origin identity.
Asserting `output.hash == input.declared_hash` conflates provenance with verification. The meaningful check is `loaded.hash == saved.hash` — does the system faithfully reproduce what it stored? Where the input came from doesn't affect whether the storage pipeline works correctly.

### Defaults belong at mutation sites, not declaration sites.
Enforcing `no_self_distill defaults true` via a Pydantic validator locks that decision into the type model forever. Putting it in the freeze path keeps the default visible at the point where it's applied, lets lint distinguish between absent-and-defaulted vs explicitly-false, and avoids modifying earlier phases' types for a policy decision.

### Abstractions cost until you need them. Then they cost less than working around their absence.
A schema version bump requires a migration strategy. Not having one means every change silently breaks backward compatibility. A `run_protection` marker table costs a few lines but prevents expensive cross-reference scans on delete. Small abstractions that encode known constraints are net positive even before their day comes.

---

## Testing anti-patterns we've encountered

### Don't test implementation details
A test that simulates `os.replace` failure by monkeypatching it only makes sense if the operation actually uses `os.replace`. When the implementation shifts away (e.g., briefs moved to SQLite-indexed storage), the test becomes meaningless — remove it.

### Rebuild-from-files after deleting the database
If you delete the DB and expect queries to return results, you're assuming filesystem artifacts contain recoverable data. With SQLite-as-authority and disk-only-for-blobs, the index is gone forever. Don't design rebuild paths around assumptions that contradict the architecture.

### Comparing saved output against input's declared hash
When an input has a pre-set `brief_hash = "a"*64` and save computes the real hash, asserting `saved.brief_hash == input.brief_hash` fails by design. Instead assert round-trip consistency: `saved.brief_hash == loaded.brief_hash`.

---

## Appended Notes

> Add new entries below this line. Format each entry as a heading with date.

### 2025-08-09 — Initial creation from Phases 2 & 3 lessons
See sections above for captured insights.

### 2026-08-08 — Phase 01 rewrite lessons (dataclass → self-validating models)

**Wire format and internal representation are two languages.** When a system has both, the mapping between them must be bidirectional and explicit. If serialization produces keys that don't match what deserialization expects, round-trips silently break — not at the boundary where the mismatch originates, but later, in unrelated code that trusts the output. Verify both directions independently.

**Derived fields must be excluded from their own computation.** A hash that includes itself is circular. Any field computed from other content must be excluded from that computation — declared explicitly per-type, not discovered by convention. Self-reference in content-addressed systems produces either infinite loops or silent corruption depending on implementation order.

**Test data must be rich enough to exercise the behavior under test.** A single-item list reversed is identical to the original. A test asserting order-sensitivity with one item passes vacuously. Fixtures must have sufficient cardinality for the assertions they make — otherwise the test proves nothing while appearing to prove everything.

**Framework internals should not leak across domain boundaries.** When a validation framework raises its own error type, wrap it at the boundary in the domain's exception type. Callers should never need to know which framework validates the data — only that validation failed and why. This preserves the ability to swap implementations without cascading changes through every caller.

**Boilerplate elimination reveals hidden invariants.** Replacing hundreds of lines of hand-written serialization with declarative validation exposes invariants that were scattered across methods as configuration on the type itself. The reduction in code is a reduction in places for bugs to hide — and a reduction in places for invariants to drift.
