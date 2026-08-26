# Write a three-section briefing

## Owner

Briefing Editor Agent

## Purpose

Select and explain the most relevant supported developments for a newcomer to finance.

## Inputs

- three section research results;
- analyst focus;
- approved editorial and display preferences.

## Output

Exactly three `BriefingSection` objects with exactly three `BriefingItem` objects in each.

Every item includes:

- headline;
- what happened;
- why it matters for this focus;
- what to watch next;
- source, URL, and publication date;
- an uncertainty note when evidence is thin.

## Method

Prefer relevance and evidence quality over novelty. Explain unfamiliar terms in place. Do not predict prices or recommend trades. If nine supported items are unavailable, preserve the shape with an explicit `insufficient evidence` result rather than inventing content.
