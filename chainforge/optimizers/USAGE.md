# Optimizer Usage Guide

This guide explains how to use the evolutionary algorithm optimizer in ChainForge for prompt optimization.

## Overview

The optimizer uses an evolutionary algorithm to iteratively improve prompts for text classification tasks by:
1. **Selection**: Choosing the best-performing prompts based on fitness metrics (MCC or Balanced Accuracy)
2. **Crossover**: Combining prompts using semantic sentence-level chunking
3. **Mutation**: Modifying prompts using either Memgraph taxonomy or simple word-level mutations
4. **Elitism**: Preserving top performers across generations

## Architecture

### Data Flow

```
PromptNode → OptimizerNode ← EvaluatorNode
                ↓
         Flask /optimize endpoint
                ↓
     evolutionary_algorithm_optimizer
                ↓
         Best optimized prompt
```

### Key Components

1. **OptimizerNode** (React frontend): UI for configuring EA parameters
2. **Flask /optimize endpoint**: Receives requests and coordinates optimization
3. **evolutionary_algorithm_optimizer**: Core EA implementation
4. **Memgraph** (optional): Provides taxonomy-based mutation templates

## How the Evaluation Function Works

### Current Implementation

The `evaluation_function` in [flask_app.py](../flask_app.py:2043) is a **closure** that:
- Receives evaluation data from the EvaluatorNode
- Returns this data for each prompt being evaluated
- The data contains `eval_res` with ground truth and predicted labels

### Expected Data Format

Evaluation data from EvaluatorNode should be:

```json
[
    {
        "text": "LLM response text",
        "prompt": "The prompt that was used",
        "eval_res": {
            "items": [
                {"true": "positive", "pred": "positive"},
                {"true": "negative", "pred": "positive"},
                ...
            ]
        }
    },
    ...
]
```

### parse_predictions Function

The `parse_predictions` function in [utils.py](utils.py:103) extracts labels:

```python
def parse_predictions(results):
    y_true = []
    y_pred = []

    for result in results:
        if "eval_res" in result:
            eval_data = result["eval_res"]
            if "items" in eval_data:
                for item in eval_data["items"]:
                    y_true.append(item["true"])
                    y_pred.append(item["pred"])

    return y_true, y_pred
```

## Usage in ChainForge UI

### Step 1: Create Initial Prompts

Use a **PromptNode** to define your initial population of prompts:

```
Classify the sentiment of the following text: {input}
```

### Step 2: Evaluate Prompts

Use an **EvaluatorNode** (CodeEvaluator or LLMEval) to evaluate prompts against test data with ground truth labels.

The evaluator should return results with `eval_res` containing:
- `items`: Array of `{true: label, pred: label}` objects

### Step 3: Configure Optimizer

Connect both nodes to **OptimizerNode** and configure:

#### Basic Settings
- **Population Size** (2-100): Number of prompts in each generation
- **Generations** (1-50): Number of evolutionary iterations
- **Mutation Rate** (0-1): Probability of mutating offspring (default: 0.3)
- **Crossover Rate** (0-1): Probability of crossover (default: 0.7)

#### Selection Method
- **Tournament** (default): Select parents via tournament competition
  - Tournament Size: Number of candidates (default: 3)
- **Roulette**: Probabilistic selection based on fitness

#### Fitness Metric
- **MCC** (default): Matthews Correlation Coefficient - good for imbalanced classes
- **Balanced Accuracy**: Average of recall for each class

#### Elitism
- **Elitism Count**: Number of best individuals to preserve (default: 2)

#### Neo4j/Memgraph Mutation (Optional)
Enable taxonomy-based mutation:
- **Neo4j URI**: `bolt://localhost:7688`
- **Username**: (leave empty for Memgraph)
- **Password**: (leave empty for Memgraph)

### Step 4: Run Optimization

Click "Run Optimizer" and wait for the algorithm to complete.

## Programmatic Usage

### Direct API Call

```python
import requests
import json

# Prepare data
initial_prompts = [
    "Classify sentiment: {input}",
    "Is this positive or negative? {input}"
]

evaluation_data = [
    {
        "text": "response1",
        "prompt": "prompt1",
        "eval_res": {
            "items": [
                {"true": "positive", "pred": "positive"},
                {"true": "negative", "pred": "negative"}
            ]
        }
    }
]

# Configure optimizer
data = {
    "method": "evolutionary_algorithm",
    "initial_prompts": json.dumps(initial_prompts),
    "evaluation_data": json.dumps(evaluation_data),
    "population_size": "10",
    "num_generations": "5",
    "mutation_rate": "0.3",
    "crossover_rate": "0.7",
    "selection_method": "tournament",
    "tournament_size": "3",
    "fitness_metric": "mcc",
    "elitism_count": "2",
    # Optional Memgraph
    "neo4j_uri": "bolt://localhost:7688",
    "neo4j_user": "",
    "neo4j_password": ""
}

# Make request
response = requests.post(
    "http://localhost:8000/optimize",
    data=data
)

result = response.json()
print("Best prompt:", result["best_prompt"])
print("Best fitness:", result["best_fitness"])
```

### Using the Registry Directly

```python
from chainforge.optimizers import OptimizerRegistry

# Get handler
handler = OptimizerRegistry.get_handler("evolutionary_algorithm")

# Define evaluation function
def evaluation_function(prompt):
    # Return evaluation results in the expected format
    return evaluation_data

# Configure settings
settings = {
    "population_size": 10,
    "num_generations": 5,
    "mutation_rate": 0.3,
    "crossover_rate": 0.7,
    "selection_method": "tournament",
    "tournament_size": 3,
    "fitness_metric": "mcc",
    "elitism_count": 2,
    "neo4j_uri": "bolt://localhost:7688",
    "neo4j_user": "",
    "neo4j_password": ""
}

# Run optimization
result = handler(initial_prompts, evaluation_function, settings)

print("Best prompt:", result["best_prompt"])
print("Best fitness:", result["best_fitness"])
print("History:", result["history"])
```

## Implementing a Custom Evaluation Function

If you want the optimizer to **actively evaluate prompts** (rather than using pre-computed evaluation data), you need to implement a proper evaluation function:

```python
def evaluation_function(prompt):
    """
    Actively evaluate a prompt by running it against test data.
    """
    from your_llm_client import call_llm

    results = []

    # Iterate through test cases
    for test_case in test_dataset:
        # Format prompt with input
        formatted_prompt = prompt.replace("{input}", test_case["input"])

        # Call LLM
        llm_response = call_llm(formatted_prompt)

        # Extract prediction (you may need to parse the response)
        prediction = extract_label(llm_response)

        # Build result in expected format
        results.append({
            "text": llm_response,
            "prompt": formatted_prompt,
            "eval_res": {
                "items": [{
                    "true": test_case["label"],
                    "pred": prediction
                }]
            }
        })

    return results
```

## Memgraph Integration

See [README_MEMGRAPH.md](README_MEMGRAPH.md) for:
- Graph schema setup
- Connection configuration
- Taxonomy-based mutation details
- Troubleshooting

## Tips for Best Results

1. **Start Small**: Begin with 5-10 prompts and 3-5 generations to test
2. **Balance Exploration/Exploitation**:
   - Higher mutation rate = more exploration
   - Higher elitism = more exploitation
3. **Use Memgraph**: Taxonomy-based mutation produces more meaningful variations
4. **Choose Right Metric**:
   - MCC for imbalanced datasets
   - Balanced Accuracy for balanced datasets
5. **Monitor Fitness**: Check if fitness improves across generations
6. **Iterate**: Use best prompt from one run as seed for next run

## Troubleshooting

### "No valid predictions" Error
- Check that `evaluation_data` has the correct format
- Ensure `eval_res.items` contains `true` and `pred` fields

### Low Fitness Scores
- Verify evaluation data contains accurate labels
- Try different selection methods or fitness metrics
- Increase population size or generations

### Mutation Not Working
- Check Memgraph is running: `docker ps | grep memgraph`
- Verify URI is correct: `bolt://localhost:7688`
- Ensure Pattern nodes exist in database

### All Prompts Look Similar
- Increase mutation rate (e.g., 0.5-0.7)
- Add more diverse initial prompts
- Use Memgraph for cross-domain mutations

## Dependencies

```bash
# Install optimizer dependencies
pip install -e .[optimizer]

# Install spaCy model for semantic crossover
python -m spacy download en_core_web_sm
```

## Example Workflow

1. **Prepare Test Data**: Create dataset with inputs and labels
2. **Create Initial Prompts**: 3-5 diverse prompt templates
3. **Set Up Evaluator**: Configure EvaluatorNode to classify responses
4. **Configure Optimizer**: Set population=10, generations=5, use MCC
5. **Run Optimization**: Wait for completion (may take several minutes)
6. **Analyze Results**: Check best_fitness and history
7. **Test Best Prompt**: Validate on held-out test set
8. **Iterate**: Use best prompt as seed for next optimization run
