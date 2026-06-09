# nb4 finding — the two goals don't cover the same area

A spine check for `planning_nb4.md`, run 2026-06-09. Reproduce with
`uv run exploration_notebooks/nb4_coverage_check.py`.

## The finding

nb4 plans to rank Cape Town suburbs by zonal stats over UTCI COGs, and to show
goal-switching by swapping the baseline COG for a street-trees cooling delta.
nb3 listed the Cape Town S3 COG keys but never opened them; nb2 opened a single
Campinas baseline COG but never compared the Cape Town baseline and delta
extents. So no one had measured the area each Cape Town layer actually covers —
nb3 only inferred it from the AOI token in each filename. That coverage is the
whole story.

The baseline and the delta cover very different areas:

| Goal | COG | Covers | Suburbs it can rank |
|---|---|---|---|
| "Reduce extreme heat" | `urban_extent` baseline | whole metro (1,334 km²) | ~150, city-wide |
| "Where would street trees cool most" | `business_district` delta | CBD only (9 km²) | 3–4 |

Of the 63 Cape Town COGs, the `urban_extent` baseline is the only one whose
AOI token marks it metro-wide; every other COG — the `business_district`
baseline and all the deltas (street trees, cool roofs, park shade, and their
combinations) — carries the CBD token. Extents were measured directly on three
representatives, one of each type: `urban_extent` → ~1,334 km², the
`business_district` baseline and a `business_district` delta → ~9 km². The 60
remaining layers are classified by that AOI token alone — now validated against
real raster bounds on the samples, but not individually opened.

So goal-switching is trivial in code — swap one COG URL — but the delta ranking
is degenerate: 3–4 suburbs is not a ranking. **The binding constraint is data
coverage, not the search algorithm.** A city-wide impact ranking is blocked by
the missing city-wide delta COG, not by compute or method. This is nb4's
headline feasibility result.

## What this means for the notebook

The delta covers only 3–4 suburbs, so it can't rank the city. Report that
limit.

Still show the goal switch: swapping one COG URL re-runs the same pipeline on
the delta. Just label the delta result degenerate, not a real top-N.

The resolution check (`planning_nb4.md` §2) is now a formality — suburbs hold
plenty of pixels. Extent is the only gate that matters.
