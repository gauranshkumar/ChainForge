# Optimizer Architecture Plan

## Current Problem

The optimizer currently expects **pre-evaluated** prompts, but the correct workflow should be:
1. Receive **prompt templates** (with variables like `{input}`)
2. Receive **test dataset** (tabular data with input/label pairs)
3. **Internally evaluate** each candidate prompt by:
   - Rendering the template with test data
   - Calling LLM for each rendered prompt
   - Comparing LLM response with ground truth
   - Calculating fitness (MCC or Balanced Accuracy)

## Proposed Architecture

### Data Flow

```
PromptNode (template) ───┐
                         ├──> OptimizerNode ──> Best Prompt Template
TabularDataNode (data) ──┤      │
                         │      │ (internally)
LLM Config ──────────────┘      ├─> Render templates
                                ├─> Call LLM
                                ├─> Evaluate responses
                                └─> Calculate fitness
```

### Input Requirements

#### 1. Prompt Template (from PromptNode)
```python
template = """
Classify the sentiment of: {input}

[DATA]
Example: "Great!" → positive
Example: "Terrible" → negative
[/DATA]

Answer: """
```

#### 2. Test Dataset (from TabularDataNode)
```python
test_data = [
    {"input": "I love this product", "label": "positive"},
    {"input": "Worst purchase ever", "label": "negative"},
    {"input": "Highly recommend", "label": "positive"},
]
```

#### 3. LLM Configuration
```python
llm_config = {
    "model": "gpt-4",
    "provider": "openai",
    "temperature": 0.0,
    "max_tokens": 10
}
```

### Evaluation Function (Core Logic)

```python
def evaluation_function(prompt_template: str) -> List[Dict]:
    """
    Evaluate a prompt template against test dataset.

    For each test case:
    1. Render template with test input
    2. Call LLM with rendered prompt
    3. Parse LLM response
    4. Compare with ground truth

    Returns evaluation results in format expected by parse_predictions.
    """
    results = []

    for test_case in test_dataset:
        # 1. Render template
        rendered_prompt = prompt_template.replace("{input}", test_case["input"])

        # 2. Call LLM
        llm_response = call_llm(
            prompt=rendered_prompt,
            model=llm_config["model"],
            provider=llm_config["provider"],
            temperature=llm_config["temperature"],
            max_tokens=llm_config["max_tokens"]
        )

        # 3. Parse response (extract classification)
        predicted_label = parse_classification(llm_response)

        # 4. Store result
        results.append({
            "text": llm_response,
            "prompt": rendered_prompt,
            "eval_res": {
                "items": [{
                    "true": test_case["label"],
                    "pred": predicted_label
                }]
            }
        })

    return results
```

### Evolutionary Loop

```python
for generation in range(num_generations):
    for individual in population:
        # Evaluate this prompt template
        eval_results = evaluation_function(individual.prompt)

        # Extract true/predicted labels
        y_true, y_pred = parse_predictions(eval_results)

        # Calculate fitness
        individual.fitness = calculate_fitness(y_true, y_pred, metric)

    # Selection, crossover, mutation (with data preservation)
    ...
```

## Implementation Changes Needed

### 1. Flask Endpoint (`/optimize`)

**Current:**
```python
def evaluation_function(prompt):
    return evaluation_data  # Pre-computed
```

**New:**
```python
def evaluation_function(prompt_template):
    results = []
    for test_case in test_dataset:
        # Render template
        rendered = render_template(prompt_template, test_case)

        # Call LLM (using ChainForge's existing LLM infrastructure)
        response = call_llm_api(
            prompt=rendered,
            llm_config=llm_config
        )

        # Parse and evaluate
        prediction = extract_label(response)
        results.append({
            "eval_res": {
                "items": [{
                    "true": test_case["label"],
                    "pred": prediction
                }]
            }
        })

    return results
```

### 2. OptimizerNode (React)

**Current Inputs:**
- `prompts`: Initial prompt strings
- `eval_data`: Pre-computed evaluation results

**New Inputs:**
- `prompt_templates`: Prompt templates with `{variables}`
- `test_dataset`: Array of `{input, label}` objects
- `llm_config`: LLM model, provider, temperature, etc.

**New UI Fields:**
- LLM Provider dropdown
- Model selection
- Temperature slider
- Max tokens input

### 3. Template Rendering

Use ChainForge's existing template system:
```python
def render_template(template: str, vars: Dict[str, Any]) -> str:
    """Render template with variables."""
    result = template
    for key, value in vars.items():
        result = result.replace(f"{{{key}}}", str(value))
    return result
```

### 4. Response Parsing

```python
def extract_label(llm_response: str, valid_labels: List[str] = None) -> str:
    """
    Extract classification label from LLM response.

    Strategies:
    1. Look for exact label match (case-insensitive)
    2. Look for label in last line
    3. Extract from "Answer: X" format
    4. First word matching valid_labels
    """
    response = llm_response.strip().lower()

    if valid_labels:
        for label in valid_labels:
            if label.lower() in response:
                return label

    # Extract last word/line
    lines = response.split('\n')
    last_line = lines[-1].strip()

    return last_line
```

## Benefits of This Approach

✅ **No Pre-Evaluation**: Optimizer handles evaluation internally
✅ **Template Optimization**: Optimizes the template, not rendered prompts
✅ **Data Preservation**: Protected sections stay intact
✅ **Real LLM Calls**: Actual fitness based on LLM performance
✅ **Flexible**: Works with any LLM provider ChainForge supports
✅ **Scalable**: Can evaluate on large test datasets

## Challenges

1. **Performance**: Many LLM calls (population_size × test_dataset_size × num_generations)
2. **Cost**: LLM API costs can add up quickly
3. **Latency**: Optimization may take minutes/hours
4. **Rate Limits**: Need to handle API rate limiting

## Solutions

1. **Caching**: Cache LLM responses for identical prompts
2. **Parallelization**: Call LLMs concurrently (async)
3. **Subset Evaluation**: Use subset of test data per generation
4. **Early Stopping**: Stop if fitness plateaus

## Example Workflow

1. **User creates prompt template:**
   ```
   Classify: {input}
   [DATA]Examples...[/DATA]
   Label:
   ```

2. **User uploads test data CSV:**
   ```
   input,label
   "Great product",positive
   "Terrible service",negative
   ```

3. **User configures optimizer:**
   - Population: 10
   - Generations: 5
   - LLM: GPT-4
   - Temperature: 0

4. **Optimizer runs:**
   - Generation 1: Tests 10 prompts × 2 data points = 20 LLM calls
   - Calculates fitness for each
   - Evolves population
   - Repeat 5 times
   - **Total: 100 LLM calls**

5. **Output: Best prompt template** with highest accuracy

## Next Steps

1. Update `flask_app.py` evaluation function to call LLMs
2. Add LLM configuration to OptimizerNode UI
3. Implement template rendering in evaluation loop
4. Add response parsing logic
5. Test end-to-end workflow
6. Add caching and optimization features
