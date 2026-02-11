---
name: write-x-post
description: Create X post or thread from article/context in Short Gravity voice
user-invocable: true
allowed-tools: Read, Write, Edit
---

# Write X Post

Generate an X post or thread from provided context.

## Format Options

### Single Post (< 280 chars)
- Punchy thesis statement
- Works standalone
- Often a question or provocative claim

### Article Post (X Articles feature)
- Full long-form content
- Rendered as article card on X
- Use `/write-article` skill for this format

### Thread
- Hook tweet + 3-8 follow-up tweets
- Each tweet stands alone but builds narrative
- End with conviction statement

## Voice Rules

### Hook Patterns That Work
- Counterintuitive claim: "The most valuable real estate on Earth is no longer on Earth."
- Question that reframes: "What if the limiting factor for AI isn't chips?"
- Historical parallel: "In 1991, commanders duct-taped $400 GPS units to helicopters..."

### Thread Structure
1. **Tweet 1 (Hook)**: Grab attention, promise value
2. **Tweets 2-4**: Build the argument with evidence
3. **Tweet 5-6**: The insight/thesis
4. **Final tweet**: Position + conviction ("Long $ASTS")

### Formatting for X
- No hashtags (looks amateur)
- Minimal emojis (one max, if any)
- Line breaks for emphasis
- Numbers and data points hit hard

## Input

Provide one of:
- Full article to condense
- Research notes/context
- Thesis to articulate

Specify: `single` | `thread` | `article`

## Output

Return the formatted post(s), ready to copy-paste.

For threads, number each tweet:
```
1/ [Hook tweet]

2/ [Building block]

3/ [Evidence]
...
```
