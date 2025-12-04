# New OptimizerNode Implementation

## Key Changes

The new implementation moves LLM evaluation to the frontend, using the `/optimize/generation` endpoint for each evolutionary step.

## New Helper Functions to Add

```typescript
// Helper: Evaluate a single prompt template against test dataset
const evaluatePrompt = async (
  promptTemplate: string,
  testDataset: any[],
  llmSpec: LLMSpec
): Promise<number> => {
  // Import necessary backend functions
  const { queryLLM } = await import("./backend/backend");
  const { extractBracketedSubstrings } = await import("./TemplateHooksComponent");

  // Results for fitness calculation
  const yTrue: string[] = [];
  const yPred: string[] = [];

  // Evaluate each test case
  for (const testCase of testDataset) {
    const inputValue = typeof testCase === "object" && "text" in testCase
      ? testCase.text
      : testCase;
    const labelValue = testCase.metavars?.label || "";

    // Render template with input
    const renderedPrompt = promptTemplate.replace(/\{input\}/g, inputValue);

    // Call LLM
    try {
      const result = await queryLLM(
        `optimizer-eval-${Date.now()}`,
        [llmSpec],
        1,
        renderedPrompt,
        {},
        undefined,
        undefined,
        true // no_cache
      );

      if (result.responses && result.responses.length > 0) {
        const response = result.responses[0];
        const responseText = typeof response.responses[0] === "string"
          ? response.responses[0]
          : "";

        // Extract prediction (simple: last line or match label)
        const prediction = responseText.trim().split("\n").pop()?.trim() || "";

        yTrue.push(labelValue);
        yPred.push(prediction);
      }
    } catch (error) {
      console.error("Error evaluating prompt:", error);
      // On error, count as incorrect
      yTrue.push(labelValue);
      yPred.push("");
    }
  }

  // Calculate fitness (MCC or Balanced Accuracy)
  return calculateFitness(yTrue, yPred, fitnessMetric);
};

// Helper: Evaluate multiple prompts
const evaluatePrompts = async (
  prompts: string[],
  testDataset: any[],
  llmSpec: LLMSpec,
  onProgress?: (completed: number, total: number) => void
): Promise<Array<{prompt: string; fitness: number}>> => {
  const results = [];

  for (let i = 0; i < prompts.length; i++) {
    const fitness = await evaluatePrompt(prompts[i], testDataset, llmSpec);
    results.push({ prompt: prompts[i], fitness });

    if (onProgress) {
      onProgress(i + 1, prompts.length);
    }
  }

  return results;
};

// Helper: Calculate fitness from predictions
const calculateFitness = (yTrue: string[], yPred: string[], metric: string): number => {
  // Simple accuracy for now (can be enhanced with MCC later)
  if (yTrue.length === 0) return 0;

  let correct = 0;
  for (let i = 0; i < yTrue.length; i++) {
    if (yTrue[i].toLowerCase() === yPred[i].toLowerCase()) {
      correct++;
    }
  }

  return correct / yTrue.length;
};
```

## New runOptimization Function

```typescript
const runOptimization = useCallback(async () => {
  const handleError = (msg: string, err?: any) => {
    console.error(msg, err);
    showAlert?.(msg);
    setStatus(Status.ERROR);
  };

  // 1) Validate inputs
  if (!promptText || promptText.trim() === "") {
    handleError("No prompt template found. Please enter a prompt template.");
    return;
  }

  if (!llmItemsCurrState || llmItemsCurrState.length === 0) {
    handleError("No LLM configured. Please add an LLM model.");
    return;
  }

  // 2) Pull test dataset
  let inputData: { input?: any[]; label?: any[] } = {};
  try {
    inputData = pullInputData(["input", "label"], id) as {
      input?: any[];
      label?: any[];
    };
  } catch (error) {
    handleError("No input data found. Connect TabularDataNode.", error);
    return;
  }

  const inputColumn = inputData.input || [];
  const labelColumn = inputData.label || [];

  if (inputColumn.length === 0 || labelColumn.length === 0) {
    handleError("No test dataset found. Connect TabularDataNode with 'input' and 'label' columns.");
    return;
  }

  // Convert to test dataset format
  const testDataset = inputColumn.map((item: any, idx: number) => {
    const inputValue = typeof item === "object" && "text" in item ? item.text : item;
    const labelValue = typeof labelColumn[idx] === "object" && "text" in labelColumn[idx]
      ? labelColumn[idx].text
      : labelColumn[idx];
    return { text: inputValue, metavars: { label: labelValue } };
  });

  setStatus(Status.LOADING);
  setJSONResponses([]);
  setOptimizationHistory([]);

  try {
    const llm = llmItemsCurrState[0];

    // Prepare settings for optimizer
    const settings = {
      population_size: populationSize,
      num_generations: numGenerations,
      mutation_rate: mutationRate,
      crossover_rate: crossoverRate,
      selection_method: selectionMethod,
      tournament_size: tournamentSize,
      fitness_metric: fitnessMetric,
      elitism_count: elitismCount,
    };

    if (useNeo4j && neo4jUri && neo4jUser && neo4jPassword) {
      settings.neo4j_uri = neo4jUri;
      settings.neo4j_user = neo4jUser;
      settings.neo4j_password = neo4jPassword;
    }

    // Initialize population with initial prompt
    let population = [{ prompt: promptText, fitness: 0 }];

    // Evaluate initial population
    const initialEval = await evaluatePrompts([promptText], testDataset, llm);
    population = initialEval;

    const history = [];
    let currentGeneration = 0;
    let bestPrompt = population[0].prompt;
    let bestFitness = population[0].fitness;

    // Main optimization loop
    while (currentGeneration < numGenerations) {
      // Call Flask to get next generation
      const response = await fetch(`${FLASK_BASE_URL}optimize/generation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          method: "evolutionary_algorithm",
          generation: currentGeneration,
          population: population,
          settings: settings,
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error || "Generation step failed");
      }

      const result = await response.json();

      // Check if complete
      if (result.complete) {
        bestPrompt = result.best_prompt;
        bestFitness = result.best_fitness;
        break;
      }

      // Evaluate new population
      const newPopulation = await evaluatePrompts(
        result.new_population,
        testDataset,
        llm,
        (completed, total) => {
          // Update progress: show which prompt is being evaluated
          console.log(`Evaluating prompt ${completed}/${total} in generation ${currentGeneration + 1}`);
        }
      );

      population = newPopulation;
      currentGeneration = result.generation;
      bestPrompt = result.best_prompt;
      bestFitness = result.best_fitness;

      // Track history
      history.push({
        generation: currentGeneration,
        best_fitness: result.best_fitness,
        avg_fitness: result.avg_fitness,
        best_prompt: result.best_prompt,
      });
    }

    // Store final results
    setBestPrompt(bestPrompt);
    setBestFitness(bestFitness);
    setOptimizationHistory(history);

    // Create responses for inspector
    const responses: LLMResponse[] = [];
    responses.push({
      uid: uuid(),
      prompt: "Best Optimized Prompt",
      vars: { fitness: bestFitness, metric: fitnessMetric },
      responses: [bestPrompt],
      llm: "Evolutionary Optimizer",
      metavars: { best_fitness: bestFitness, fitness_metric: fitnessMetric },
    });

    history.forEach((gen: any) => {
      responses.push({
        uid: uuid(),
        prompt: `Generation ${gen.generation}`,
        vars: {
          generation: gen.generation,
          best_fitness: gen.best_fitness,
          avg_fitness: gen.avg_fitness,
        },
        responses: [gen.best_prompt],
        llm: "Evolutionary Optimizer",
        metavars: {
          generation: gen.generation,
          best_fitness: gen.best_fitness,
          avg_fitness: gen.avg_fitness,
        },
      });
    });

    setJSONResponses(responses);

    // Output for downstream nodes
    const outputData: TemplateVarInfo = {
      text: bestPrompt,
      prompt: "",
      fill_history: {
        optimizer: "Evolutionary Algorithm",
        fitness: bestFitness,
      },
      llm: undefined,
      metavars: {
        fitness: bestFitness,
        metric: fitnessMetric,
        generations: numGenerations,
      },
    };

    setDataPropsForNode(id, {
      best_prompt: bestPrompt,
      best_fitness: bestFitness,
      history: history,
      optimized_prompt: outputData,
    });
    pingOutputNodes(id);

    setStatus(Status.READY);
  } catch (err: any) {
    handleError(`Error during optimization: ${err.message}`, err);
  }
}, [
  id,
  promptText,
  llmItemsCurrState,
  populationSize,
  numGenerations,
  mutationRate,
  crossoverRate,
  selectionMethod,
  tournamentSize,
  fitnessMetric,
  elitismCount,
  useNeo4j,
  neo4jUri,
  neo4jUser,
  neo4jPassword,
  pullInputData,
  setDataPropsForNode,
  showAlert,
  pingOutputNodes,
]);
```

## Summary

This new implementation:
1. ✅ Works with ALL frontend LLM providers (Ollama, OpenAI, etc.)
2. ✅ No need for custom provider scripts
3. ✅ Uses the new `/optimize/generation` endpoint
4. ✅ Frontend evaluates prompts using `queryLLM` from backend.ts
5. ✅ Progress can be tracked for each evaluation
6. ✅ Simple fitness calculation (can be enhanced)

The optimization now runs as a loop in the frontend, calling Flask for genetic operations only.
