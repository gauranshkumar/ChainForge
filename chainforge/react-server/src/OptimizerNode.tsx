import React, {
  useState,
  useEffect,
  useCallback,
  useRef,
  useContext,
} from "react";
import { Handle, Position } from "reactflow";
import {
  NumberInput,
  NativeSelect,
  Text,
  Stack,
  TextInput,
  Accordion,
  Group,
  Switch,
  Button,
} from "@mantine/core";
import { Status } from "./StatusIndicatorComponent";
import { AlertModalContext } from "./AlertModal";
import BaseNode from "./BaseNode";
import NodeLabel from "./NodeLabelComponent";
import useStore from "./store";
import LLMResponseInspectorModal, {
  LLMResponseInspectorModalRef,
} from "./LLMResponseInspectorModal";
import InspectFooter from "./InspectFooter";
import { IconSearch, IconChartLine } from "@tabler/icons-react";
import { TemplateVarInfo, LLMResponse } from "./backend/typing";
import { FLASK_BASE_URL } from "./backend/utils";
import { v4 as uuid } from "uuid";

interface OptimizerNodeData {
  title?: string;
  population_size?: number;
  num_generations?: number;
  mutation_rate?: number;
  crossover_rate?: number;
  selection_method?: string;
  tournament_size?: number;
  fitness_metric?: string;
  elitism_count?: number;
  neo4j_uri?: string;
  neo4j_user?: string;
  neo4j_password?: string;
  refresh?: boolean;
}

interface OptimizerNodeProps {
  data: OptimizerNodeData;
  id: string;
}

const OptimizerNode: React.FC<OptimizerNodeProps> = ({ data, id }) => {
  const nodeDefaultTitle = "Optimizer Node";
  const nodeIcon = "🧬";

  const pullInputData = useStore((s) => s.pullInputData);
  const setDataPropsForNode = useStore((s) => s.setDataPropsForNode);
  const pingOutputNodes = useStore((s) => s.pingOutputNodes);
  const showAlert = useContext(AlertModalContext);

  const [status, setStatus] = useState<Status>(Status.NONE);
  const [jsonResponses, setJSONResponses] = useState<LLMResponse[]>([]);
  const [optimizationHistory, setOptimizationHistory] = useState<any[]>([]);
  const [bestPrompt, setBestPrompt] = useState<string>("");
  const [bestFitness, setBestFitness] = useState<number>(0);

  // Optimizer settings
  const [populationSize, setPopulationSize] = useState(
    data.population_size || 10,
  );
  const [numGenerations, setNumGenerations] = useState(
    data.num_generations || 5,
  );
  const [mutationRate, setMutationRate] = useState(data.mutation_rate || 0.3);
  const [crossoverRate, setCrossoverRate] = useState(
    data.crossover_rate || 0.7,
  );
  const [selectionMethod, setSelectionMethod] = useState(
    data.selection_method || "tournament",
  );
  const [tournamentSize, setTournamentSize] = useState(
    data.tournament_size || 3,
  );
  const [fitnessMetric, setFitnessMetric] = useState(
    data.fitness_metric || "mcc",
  );
  const [elitismCount, setElitismCount] = useState(data.elitism_count || 2);
  const [useNeo4j, setUseNeo4j] = useState(false);
  const [neo4jUri, setNeo4jUri] = useState(data.neo4j_uri || "");
  const [neo4jUser, setNeo4jUser] = useState(data.neo4j_user || "");
  const [neo4jPassword, setNeo4jPassword] = useState(data.neo4j_password || "");

  const inspectorRef = useRef<LLMResponseInspectorModalRef>(null);

  // On refresh
  useEffect(() => {
    if (data.refresh) {
      setDataPropsForNode(id, { refresh: false });
      setJSONResponses([]);
      setStatus(Status.NONE);
      setOptimizationHistory([]);
      setBestPrompt("");
      setBestFitness(0);
    }
  }, [data.refresh, id, setDataPropsForNode]);

  // Save settings when they change
  useEffect(() => {
    setDataPropsForNode(id, {
      population_size: populationSize,
      num_generations: numGenerations,
      mutation_rate: mutationRate,
      crossover_rate: crossoverRate,
      selection_method: selectionMethod,
      tournament_size: tournamentSize,
      fitness_metric: fitnessMetric,
      elitism_count: elitismCount,
      neo4j_uri: neo4jUri,
      neo4j_user: neo4jUser,
      neo4j_password: neo4jPassword,
    });
  }, [
    id,
    populationSize,
    numGenerations,
    mutationRate,
    crossoverRate,
    selectionMethod,
    tournamentSize,
    fitnessMetric,
    elitismCount,
    neo4jUri,
    neo4jUser,
    neo4jPassword,
    setDataPropsForNode,
  ]);

  // Main optimization function
  const runOptimization = useCallback(async () => {
    const handleError = (msg: string, err?: any) => {
      console.error(msg, err);
      showAlert?.(msg);
      setStatus(Status.ERROR);
    };

    // 1) Pull initial prompts from upstream
    let inputData: { prompts?: TemplateVarInfo[]; eval_data?: any[] } = {};
    try {
      inputData = pullInputData(["prompts", "eval_data"], id) as {
        prompts?: TemplateVarInfo[];
        eval_data?: any[];
      };
    } catch (error) {
      handleError(
        "No input data found. Connect PromptNode and EvaluatorNode.",
        error,
      );
      return;
    }

    const promptsArr = inputData.prompts || [];
    const evalData = inputData.eval_data || [];

    if (promptsArr.length === 0) {
      handleError("No initial prompts found. Please provide initial prompts.");
      return;
    }

    setStatus(Status.LOADING);
    setJSONResponses([]);
    setOptimizationHistory([]);

    try {
      const formData = new FormData();
      formData.append("method", "evolutionary_algorithm");
      formData.append(
        "initial_prompts",
        JSON.stringify(promptsArr.map((p) => p.text)),
      );
      formData.append("evaluation_data", JSON.stringify(evalData));

      // Add all settings
      formData.append("population_size", String(populationSize));
      formData.append("num_generations", String(numGenerations));
      formData.append("mutation_rate", String(mutationRate));
      formData.append("crossover_rate", String(crossoverRate));
      formData.append("selection_method", selectionMethod);
      formData.append("tournament_size", String(tournamentSize));
      formData.append("fitness_metric", fitnessMetric);
      formData.append("elitism_count", String(elitismCount));

      if (useNeo4j && neo4jUri && neo4jUser && neo4jPassword) {
        formData.append("neo4j_uri", neo4jUri);
        formData.append("neo4j_user", neo4jUser);
        formData.append("neo4j_password", neo4jPassword);
      }

      const res = await fetch(`${FLASK_BASE_URL}optimize`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Optimization request failed");
      }

      const result = await res.json();

      // Store results
      setBestPrompt(result.best_prompt);
      setBestFitness(result.best_fitness);
      setOptimizationHistory(result.history || []);

      // Create responses for inspector
      const responses: LLMResponse[] = [];

      // Add best prompt
      responses.push({
        uid: uuid(),
        prompt: "Best Optimized Prompt",
        vars: {
          fitness: result.best_fitness,
          metric: fitnessMetric,
        },
        responses: [result.best_prompt],
        llm: "Evolutionary Optimizer",
        metavars: {
          best_fitness: result.best_fitness,
          fitness_metric: fitnessMetric,
        },
      });

      // Add generation history
      result.history?.forEach((gen: any, idx: number) => {
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

      // Output the best prompt for downstream nodes
      const outputData: TemplateVarInfo = {
        text: result.best_prompt,
        prompt: "",
        fill_history: {
          optimizer: "Evolutionary Algorithm",
          fitness: result.best_fitness,
        },
        llm: undefined,
        metavars: {
          fitness: result.best_fitness,
          metric: fitnessMetric,
          generations: numGenerations,
        },
      };

      setDataPropsForNode(id, {
        best_prompt: result.best_prompt,
        best_fitness: result.best_fitness,
        history: result.history,
        optimized_prompt: outputData,
      });
      pingOutputNodes(id);

      setStatus(Status.READY);
    } catch (err: any) {
      handleError(`Error during optimization: ${err.message}`, err);
    }
  }, [
    id,
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

  // Open inspector
  const openInspector = () => {
    if (jsonResponses.length > 0 && inspectorRef.current) {
      inspectorRef.current.trigger();
    }
  };

  return (
    <BaseNode nodeId={id} classNames="optimizer-node">
      <Handle
        type="target"
        position={Position.Left}
        id="prompts"
        style={{ top: "30%" }}
      />
      <Handle
        type="target"
        position={Position.Left}
        id="eval_data"
        style={{ top: "70%" }}
      />

      <NodeLabel
        title={data.title || nodeDefaultTitle}
        nodeId={id}
        icon={nodeIcon}
        status={status}
        handleRunClick={runOptimization}
        runButtonTooltip="Run evolutionary optimization"
      />

      <Stack spacing="xs" p="sm">
        <Group position="apart">
          <Text size="sm" weight={500}>
            Population Size
          </Text>
          <NumberInput
            value={populationSize}
            onChange={(val) =>
              typeof val === "number" && setPopulationSize(val)
            }
            min={2}
            max={100}
            size="xs"
            w={80}
          />
        </Group>

        <Group position="apart">
          <Text size="sm" weight={500}>
            Generations
          </Text>
          <NumberInput
            value={numGenerations}
            onChange={(val) =>
              typeof val === "number" && setNumGenerations(val)
            }
            min={1}
            max={50}
            size="xs"
            w={80}
          />
        </Group>

        <Group position="apart">
          <Text size="sm" weight={500}>
            Mutation Rate
          </Text>
          <NumberInput
            value={mutationRate}
            onChange={(val) => typeof val === "number" && setMutationRate(val)}
            min={0}
            max={1}
            step={0.1}
            precision={2}
            size="xs"
            w={80}
          />
        </Group>

        <Group position="apart">
          <Text size="sm" weight={500}>
            Crossover Rate
          </Text>
          <NumberInput
            value={crossoverRate}
            onChange={(val) => typeof val === "number" && setCrossoverRate(val)}
            min={0}
            max={1}
            step={0.1}
            precision={2}
            size="xs"
            w={80}
          />
        </Group>

        <Group position="apart">
          <Text size="sm" weight={500}>
            Fitness Metric
          </Text>
          <NativeSelect
            value={fitnessMetric}
            onChange={(e) => setFitnessMetric(e.target.value)}
            data={[
              { value: "mcc", label: "MCC" },
              { value: "balanced_accuracy", label: "Balanced Accuracy" },
            ]}
            size="xs"
            w={150}
          />
        </Group>

        <Group position="apart">
          <Text size="sm" weight={500}>
            Selection Method
          </Text>
          <NativeSelect
            value={selectionMethod}
            onChange={(e) => setSelectionMethod(e.target.value)}
            data={[
              { value: "tournament", label: "Tournament" },
              { value: "roulette", label: "Roulette Wheel" },
            ]}
            size="xs"
            w={150}
          />
        </Group>

        {selectionMethod === "tournament" && (
          <Group position="apart">
            <Text size="sm" weight={500}>
              Tournament Size
            </Text>
            <NumberInput
              value={tournamentSize}
              onChange={(val) =>
                typeof val === "number" && setTournamentSize(val)
              }
              min={2}
              max={10}
              size="xs"
              w={80}
            />
          </Group>
        )}

        <Group position="apart">
          <Text size="sm" weight={500}>
            Elitism Count
          </Text>
          <NumberInput
            value={elitismCount}
            onChange={(val) => typeof val === "number" && setElitismCount(val)}
            min={0}
            max={10}
            size="xs"
            w={80}
          />
        </Group>

        <Accordion mt="md">
          <Accordion.Item value="neo4j">
            <Accordion.Control>
              <Group>
                <Switch
                  checked={useNeo4j}
                  onChange={(e) => setUseNeo4j(e.currentTarget.checked)}
                  label="Neo4j Mutation"
                  size="sm"
                />
              </Group>
            </Accordion.Control>
            <Accordion.Panel>
              <Stack spacing="xs">
                <TextInput
                  label="Neo4j URI"
                  placeholder="bolt://localhost:7687"
                  value={neo4jUri}
                  onChange={(e) => setNeo4jUri(e.target.value)}
                  size="xs"
                  disabled={!useNeo4j}
                />
                <TextInput
                  label="Username"
                  placeholder="neo4j"
                  value={neo4jUser}
                  onChange={(e) => setNeo4jUser(e.target.value)}
                  size="xs"
                  disabled={!useNeo4j}
                />
                <TextInput
                  label="Password"
                  type="password"
                  value={neo4jPassword}
                  onChange={(e) => setNeo4jPassword(e.target.value)}
                  size="xs"
                  disabled={!useNeo4j}
                />
              </Stack>
            </Accordion.Panel>
          </Accordion.Item>
        </Accordion>

        {bestPrompt && (
          <Stack mt="md" spacing="xs">
            <Text size="sm" weight={700} color="green">
              Best Fitness: {bestFitness.toFixed(4)}
            </Text>
            <Text size="xs" color="dimmed">
              {bestPrompt.substring(0, 100)}
              {bestPrompt.length > 100 ? "..." : ""}
            </Text>
          </Stack>
        )}
      </Stack>

      {jsonResponses && jsonResponses.length > 0 && (
        <InspectFooter
          onClick={openInspector}
          showDrawerButton={false}
          onDrawerClick={() => {
            // Do nothing
          }}
          isDrawerOpen={false}
          label={
            <>
              View Results <IconSearch size="12pt" />
            </>
          }
        />
      )}

      <LLMResponseInspectorModal
        ref={inspectorRef}
        jsonResponses={jsonResponses}
      />

      <Handle
        type="source"
        position={Position.Right}
        id="optimized_prompt"
        style={{ top: "50%" }}
      />
    </BaseNode>
  );
};

export default OptimizerNode;
