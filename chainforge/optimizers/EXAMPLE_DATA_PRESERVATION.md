# Data Preservation in Optimizer

This example shows how the optimizer preserves data sections while optimizing prompts.

## Problem

When you have a prompt with embedded data (like few-shot examples), you want to optimize the instruction text while keeping the data intact.

## Solution

The optimizer automatically detects and preserves data sections marked with:
1. `[DATA]...[/DATA]` tags
2. Code blocks (` ``` ... ``` `)
3. Lines starting with `Example:`, `Input:`, `Output:`, `Q:`, `A:`

## Example

### Input Prompt

```
Classify the sentiment of the following text as positive or negative.

[DATA]
Example: "This movie was amazing!" → positive
Example: "I hated every minute of it." → negative
Example: "Best purchase ever!" → positive
[/DATA]

Provide only the label in your response.
```

###During Optimization

The optimizer will:
- **Mutate**: "Classify the sentiment..." and "Provide only..."
- **Preserve**: The entire `[DATA]...[/DATA]` section unchanged
- **Never split**: Crossover won't break data into parts

### Possible Mutated Outputs

**Generation 1:**
```
Determine whether the text expresses positive or negative sentiment.

[DATA]
Example: "This movie was amazing!" → positive
Example: "I hated every minute of it." → negative
Example: "Best purchase ever!" → positive
[/DATA]

Return just the sentiment label.
```

**Generation 2:**
```
Analyze the emotional tone and classify as positive or negative.

[DATA]
Example: "This movie was amazing!" → positive
Example: "I hated every minute of it." → negative
Example: "Best purchase ever!" → positive
[/DATA]

Output the classification only.
```

**Generation 3 (Best):**
```
Based on the examples below, classify the sentiment.

[DATA]
Example: "This movie was amazing!" → positive
Example: "I hated every minute of it." → negative
Example: "Best purchase ever!" → positive
[/DATA]

Answer with one word: positive or negative.
```

Notice how the `[DATA]` section **never changes** across generations!

## Alternative Markup Styles

### Using Code Blocks

```
Classify sentiment for the given text.

\```
Examples:
"Great product!" → positive
"Terrible service" → negative
\```

Output format: positive/negative
```

### Using Example: Prefix

```
Classify the sentiment.

Example: "I love this!" → positive
Example: "Worst ever" → negative
Example: "Highly recommend" → positive

Return the label.
```

### Multiple Data Sections

```
Classify sentiment based on these examples.

[DATA]
Positive examples:
- "Amazing!"
- "Love it!"
[/DATA]

Use the format below.

[DATA]
Format: sentiment_label
[/DATA]
```

All `[DATA]` sections are preserved independently!

## How It Works

### 1. Splitting

```python
segments, is_data_flags = split_preserving_data(prompt)
# segments = [
#     "Classify sentiment...\n\n",
#     "[DATA]\nExample: ...\n[/DATA]",
#     "\n\nProvide only..."
# ]
# is_data_flags = [False, True, False]
```

### 2. Mutation (only on False segments)

```python
mutable_text = " ".join([seg for seg, is_data in zip(segments, is_data_flags) if not is_data])
# mutable_text = "Classify sentiment... Provide only..."

# Apply mutation
mutated_text = apply_mutation(mutable_text)
```

### 3. Reconstruction

```python
result = reconstruct_with_data(mutated_text, segments, is_data_flags)
# Inserts mutated_text back, keeps [DATA] sections unchanged
```

## Workflow in ChainForge

1. **Create Initial Prompt** with data sections marked
2. **Connect to Optimizer Node**
3. **Run Optimization** - data is automatically preserved
4. **Get Best Prompt** with optimized instructions and intact data

## Tips

1. **Always mark data**: Use `[DATA]...[/DATA]` for explicit protection
2. **Code blocks work**: Use ` ``` ` for multi-line examples
3. **Example prefix**: Start lines with `Example:` for automatic detection
4. **Multiple sections**: You can have many `[DATA]` blocks
5. **Nested protection**: Regex patterns protect entire blocks

## Testing Data Preservation

```python
from chainforge.optimizers.utils import split_preserving_data

prompt = """
Classify this text.

[DATA]
Example 1: positive
Example 2: negative
[/DATA]

Return the label.
"""

segments, is_data = split_preserving_data(prompt)
print(f"Segments: {len(segments)}")
print(f"Protected: {sum(is_data)}")
# Output:
# Segments: 3
# Protected: 1
```

## Benefits

- **Preserve Examples**: Few-shot examples stay consistent
- **Maintain Format**: Output format instructions unchanged
- **Keep Data Integrity**: No corruption of training data
- **Focus Optimization**: Only instruction text evolves
- **Predictable Behavior**: Data sections never mutate unexpectedly
