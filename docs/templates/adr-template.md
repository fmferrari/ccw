# ADR Template

ADRs live in `docs/adr/` and use sequential numbering:
`0001-slug.md`, `0002-slug.md`, and so on.

## Template

```md
# {Short title of the decision}

{1-3 sentences: what's the context, what did we decide, and why.}
```

That is enough for most ADRs. The value is in recording that a decision was
made and why, not in filling out ceremony.

## Optional sections

Only include these when they add real value:

- `Status`: `proposed | accepted | deprecated | superseded by ADR-NNNN`
- `Considered Options`
- `Consequences`

## When to write an ADR

All three of these should be true:

1. Hard to reverse
2. Surprising without context
3. The result of a real trade-off

If a choice is easy to reverse or obvious from the code, skip the ADR.
