# Data Preservation Feature

## Overview

The optimizer now automatically preserves data sections in prompts during evolution, allowing you to optimize instruction text while keeping examples, templates, and other data intact.

## Quick Start

### Mark Your Data

Wrap data sections with `[DATA]...[/DATA]`:

```
Classify the sentiment as positive or negative.

[DATA]
Example: "Great product!" → positive
Example: "Terrible service" → negative
Example: "Amazing quality" → positive
[/DATA]

Output format: one word only.
```

### What Gets Protected

The optimizer automatically preserves:
- `[DATA]...[/DATA]` blocks
- Code blocks (` ``` ... ``` `)
- Lines starting with: `Example:`, `Input:`, `Output:`, `Q:`, `A:`

### What Gets Optimized

Everything else! The instruction text evolves while data stays constant.

## Example Evolution

**Initial:**
```
Classify sentiment.
[DATA]Examples...[/DATA]
Output: label
```

**Generation 3:**
```
Determine if text is positive or negative.
[DATA]Examples...[/DATA]
Return one word: positive or negative.
```

**Generation 5:**
```
Based on the examples, classify the sentiment.
[DATA]Examples...[/DATA]
Answer with classification only.
```

Notice: `[DATA]Examples...[/DATA]` **never changes**!

## Usage

1. Create prompt with `[DATA]` markers
2. Connect to OptimizerNode
3. Run - data preserved automatically
4. Get best optimized prompt with intact data

## Benefits

✅ Few-shot examples stay consistent
✅ Output formats unchanged
✅ Data integrity maintained
✅ Focus evolution on instructions
✅ No manual intervention needed

## Technical Details

See [EXAMPLE_DATA_PRESERVATION.md](EXAMPLE_DATA_PRESERVATION.md) for detailed examples and [utils.py](utils.py) for implementation (`split_preserving_data` function).
