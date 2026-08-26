# Learn briefing preferences

## Owner

Feedback and Memory Agent

## Purpose

Translate natural-language feedback into a small, typed presentation preference that a human can inspect and approve.

## Inputs

- feedback text;
- current preferences;
- the briefing the person reviewed.

## Output

A `PreferencePatch` with independent optional fields for research, editorial, and display preferences.

## Method

1. Extract only durable preferences, not one-off factual corrections.
2. Keep research, editorial, and display changes separate.
3. Show the proposed patch in plain language.
4. Never change factual evidence or source records.
5. Never write preferences directly.
6. Persist a new version only after the UI records explicit approval.

After approval, the application writes the typed patch through Agno `MemoryManager` as a `UserMemory`
record. The agent does not perform this write itself. Skills are never rewritten by feedback.
