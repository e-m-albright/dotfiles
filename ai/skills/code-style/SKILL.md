---
name: code-style
description: The aesthetic / craft pole of the code-health portfolio — a grumpy, taste-driven principal engineer that pushes already-correct, already-clear code toward genuine elegance — conceptual integrity, inevitability, exact naming, symmetry, negative space, the right abstraction, honest types. Grounded in THIS repo's doctrine (ENGINEERING.md, docs/stacks taste, the form-* lenses) so it raises code to OUR house aesthetic, not generic prettiness. Use when the user says "make this elegant / beautiful / artful", "the best code possible", "polish this to perfection", "make it sing", "what would a master (or a grumpy principal) write here", "is this actually elegant", "refine the craft", "aesthetic pass", "make it tasteful". SKIP for correctness/bugs (/review), architecture & seams (form-deepen), newcomer legibility (form-clarify), deletion (form-prune), mechanical refactors (form-tidy), or throwaway prototypes.
metadata:
  type: reference
---

# Code-Style

> **Canon** — the aesthetic enforcement of P5 (*simplicity is the goal*), P2 (*type the domain*), P3 (*one source of truth*) and the kernel's "write code that reads like the surrounding code." Behavior-preserving (Tier A); safety verified by tests, "better" gated by taste and recorded. See [ENGINEERING.md](../../../ENGINEERING.md).

The **aesthetic pole** of the portfolio. The other form lenses make code *correct* (Tier B), *deep* (form-deepen), *legible to a newcomer* (form-clarify), *minimal* (form-prune), *testable* (form-purify), *tidy* (form-tidy). This one does the last thing, the thing none of them name: it makes code **elegant** — the work of a senior, grumpy, aesthetically uncompromising principal who reads your already-passing, already-clear code and is still not satisfied.

Its standard is not "match the average neighbor." Its standard is **the best code that could exist here** — and it uses the surrounding code and `docs/stacks/` taste as the *floor* it must clear, never the ceiling it settles for.

## The bar: read it aloud as the grumpy principal

Elegance is recognized, not measured. So the core move is a **reading**: voice the harshest tasteful principal you can imagine and read the code line by line. Every place they'd wince, sigh, or ask "why is this *here*?" is a finding. Keep rewriting until the reading is silent. The dimensions they wince at:

1. **Conceptual integrity** — the code is *about one thing*, and that thing is obvious. No second idea smuggled in, no concern bleeding across the seam. (Brooks: integrity is the most important property of a design.)
2. **Inevitability** — it reads as *the only way it could be*. No visible arbitrary choices, no "we did it this way because of a meeting in 2024." The reader never has to forgive anything.
3. **Naming as the soul** — the *exact* word, never a near-synonym. Names carry the meaning so the structure can carry the mechanism; the code reads like prose. A name that needs a comment is a name that lost.
4. **Symmetry & rhythm** — things that are the same *look* the same; things that differ *look* different. Parallel cases have parallel shape. Asymmetry is a claim that there's a difference — if there isn't, it's a lie.
5. **Negative space** — elegance is mostly what's *absent*. Collapsed cases, removed ceremony, the guard clause that deletes a level of nesting, the early return that deletes an `else`. The shortest path that is still honest.
6. **The right abstraction** — deep and load-bearing; it makes the hard thing trivial. Not one too many (speculative, anemic, a pass-through) nor one too few (the duplication that wants a name). The Metz line: prefer duplication over the *wrong* abstraction; prefer the *right* abstraction over both.
7. **Honest types** — illegal states unrepresentable, errors as values, the type tells the whole truth so the reader and the compiler can trust it. A `dict[str, Any]` at a boundary is an aesthetic failure before it's a correctness one.
8. **Linearity** — reads top to bottom; the happy path is the straight line; the exceptional cases get out of the way early. No yo-yo, no "scroll up to understand down."
9. **No cleverness rent-free** — a flourish is allowed only when it pays the reader back more than it costs them. Clever that saves three lines and costs a double-take is a loss. The grumpy principal *hates* being made to feel slow.
10. **Wholeness** — comment density, error idiom, naming scheme, and shape all match the module's register. The code feels written by one hand with one taste, not assembled.

## Process

### 1. Tune the aesthetic to *this house*

Read first, so the taste you apply is the repo's, not a generic one:
- [`ENGINEERING.md`](../../../ENGINEERING.md) — the doctrine the elegance must serve (the IDs give you the *why* to cite).
- `docs/stacks/<lang>.md` — the per-language pick/avoid idioms (the house dialect).
- **The surrounding module** — the existing best code in this area. Find the most elegant thing already here; that's the floor. Match its register where it's already good; raise it where it isn't.

This is what keeps the pass from importing a foreign aesthetic — elegance *here* means elegant *in our dialect*.

### 2. The reading

Read the target aloud as the grumpy principal. Mark every wince against the ten dimensions, `file:line` + which dimension + the specific objection. Be ruthless and specific — "this name is vague" is useless; "`data` could be `pending_renewals`; the type already says it's a dict" is a finding.

### 3. Propose the elegant form — and grill it

For each finding, show the **before → after** and name what it buys (which dimension, which Canon ID). Then turn the same harshness on your *own* rewrite:
- **Does it pay?** A change that only swaps one defensible choice for another preferred one is *fussiness*, not craft — drop it. Taste is not the same as preference; only ship the change a great engineer would defend, not merely accept.
- **Does it preserve behavior?** This is Tier A. If a test can't confirm it, it's not safe yet — write the test or don't make the change.
- **Does it fight a sibling lens?** Elegance can over-collapse (hurting form-clarify's legibility) or over-extract (the wrong abstraction). When consistency-with-corpus and elegance disagree, **elegance wins but records why** (an ADR), so the next pass doesn't undo it. When the local idiom is *itself* the ugliness, elevate it and flag the systemic pattern — don't propagate it.

### 4. Graduate the systemic ones

A wince that recurs across the repo isn't a local fix — it's a missing rule. Per the repo's deterministic-spine doctrine: if the ugliness is grep-able (raw `echo` where `print_utils` exists, `dict[str, Any]` at a boundary, chained `&&` in a recipe), propose it as a `just lint-*` gate or a ratchet family so taste becomes a floor that can't regress. If it's irreducibly semantic, it stays a finding for the next aesthetic pass. *Taste, made durable* — the same bridge `converge` uses.

## What elegance looks like (the register)

Tiny, language-agnostic — the *shape* of the move, not a catalogue:

- **Collapse the case.** `if x: return True\n else: return False` → `return x`. The `else` was ceremony; the boolean was already the answer.
- **Name the concept, delete the comment.** `# the ones we haven't billed yet` over `items` → rename to `unbilled`; the comment was a name in hiding.
- **Make the illegal unrepresentable.** A `status: str` validated in five places → a closed enum/union; the validation vanishes because the type already forbids the bad state.
- **Let the happy path be straight.** Three nested `if`s guarding the real work → three guard clauses that exit early; the real work un-indents to the left margin where it belongs.

Each is behavior-preserving, each *removes* something, each makes the next reader faster. That's the texture of elegant code: not more — *less, and exact*.

## When NOT to reach for it

- The code is **wrong** → [/review](../review/SKILL.md) or [systematic-debugging](../systematic-debugging/SKILL.md). Elegance is for code that already works.
- The problem is **architecture / coupling / seams** → [form-deepen](../form-deepen/SKILL.md). Code-style polishes within a structure; it doesn't redraw it.
- The problem is **a newcomer can't follow it** → [form-clarify](../form-clarify/SKILL.md). Legibility-for-outsiders and elegance overlap but aren't the same; the most elegant code is sometimes terse.
- It's a **prototype / spike** → leave it ugly on purpose; spend the taste budget on code that will live.

## See also
- [code-health](../code-health/SKILL.md) — the router; reach for it if unsure which lens fits.
- [converge](../converge/SKILL.md) — the measured engine; run it first to remove slop/duplication, then code-style for the elegance a metric can't see.
- [ENGINEERING.md](../../../ENGINEERING.md) — the doctrine the aesthetic serves; cite IDs in findings so a taste call is anchored, not asserted.
