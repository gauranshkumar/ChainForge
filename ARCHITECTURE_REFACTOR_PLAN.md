# Optimizer Architecture Refactor Plan

## Problem
The optimizer expects Python-based LLM providers in Flask's `ProviderRegistry`, but all built-in providers (OpenAI, Anthropic, Ollama, etc.) are only available in the frontend (TypeScript/JavaScript).

## Solution: Frontend-Driven Evaluation

Instead of Flask calling LLMs, the **frontend evaluates all candidate prompts** and Flask only handles the optimization logic (selection, crossover, mutation, fitness calculation).

## New Architecture

### Approach: Frontend Evaluation Loop

The frontend runs the optimization loop, calling Flask for each generation:

```
1. Frontend: Initialize population with initial prompts
2. Frontend: Evaluate initial population using LLM calls → get fitness scores
3. FOR each generation:
   a. Frontend → Flask: Send current population + fitness scores
   b. Flask: Run selection, crossover, mutation → return new population
   c. Frontend: Evaluate new population using LLM calls → get fitness scores
4. Frontend: Get best prompt from final population
```

### API Changes

#### New Endpoint: `/optimize/generation` (POST)
**Input:**
```json
{
  "method": "evolutionary_algorithm",
  "generation": 0,
  "population": [
    {"prompt": "...", "fitness": 0.85},
    {"prompt": "...", "fitness": 0.72},
    ...
  ],
  "settings": {
    "mutation_rate": 0.3,
    "crossover_rate": 0.7,
    "selection_method": "tournament",
    ...
  }
}
```

**Output:**
```json
{
  "new_population": ["prompt1", "prompt2", ...],
  "generation": 1,
  "best_fitness": 0.85,
  "avg_fitness": 0.67
}
```

### Implementation Steps

1. **Flask (Backend)**:
   - Create `/optimize/generation` endpoint
   - Modify `evolutionary.py` to accept population with fitness scores
   - Remove LLM calling code from evolutionary algorithm
   - Return new prompts that need evaluation

2. **Frontend (OptimizerNode)**:
   - Implement `evaluatePrompts()` function that:
     - Takes array of prompt templates
     - Renders each with test data
     - Calls LLM for each rendered prompt
     - Parses responses and calculates fitness
     - Returns fitness scores
   - Implement optimization loop:
     - Evaluate initial prompts
     - FOR each generation:
       - Call `/optimize/generation` with current population + fitness
       - Evaluate returned prompts
       - Update progress UI
     - Return best prompt

### Benefits

✅ **Works with ALL LLM providers** - Uses frontend's existing LLM infrastructure
✅ **No custom providers needed** - Ollama, OpenAI, Anthropic all work out of the box
✅ **Progress visibility** - Frontend controls the loop, can show real-time progress
✅ **Simpler Flask code** - No async LLM calls, just pure optimization logic
✅ **Better error handling** - Frontend can catch and display LLM errors per prompt

### Drawbacks

⚠️ **More network requests** - One request per generation instead of one total
⚠️ **Frontend complexity** - Optimization loop now in TypeScript instead of Python
⚠️ **No server-side caching** - Each evaluation happens fresh in frontend

### Migration

- Old `/optimize` endpoint remains for custom providers
- New `/optimize/generation` endpoint for built-in providers
- OptimizerNode detects provider type and chooses appropriate flow

