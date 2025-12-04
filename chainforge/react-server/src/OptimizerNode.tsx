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
  Textarea,
  Modal,
  Code,
  Paper,
  Divider,
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
import { IconSearch, IconEye } from "@tabler/icons-react";
import { TemplateVarInfo, LLMResponse, LLMSpec } from "./backend/typing";
import { FLASK_BASE_URL } from "./backend/utils";
import { v4 as uuid } from "uuid";
import { LLMListContainer, LLMListContainerRef } from "./LLMListComponent";
import TemplateHooks, {
  extractBracketedSubstrings,
} from "./TemplateHooksComponent";

interface OptimizerNodeData {
  title?: string;
  // Prompt fields (from PromptNode)
  prompt?: string;
  vars?: string[];
  llms?: LLMSpec[];
  // Optimization fields
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
  const [neo4jUri, setNeo4jUri] = useState(
    data.neo4j_uri || "bolt://localhost:7688",
  );
  const [neo4jUser, setNeo4jUser] = useState(data.neo4j_user || "");
  const [neo4jPassword, setNeo4jPassword] = useState(data.neo4j_password || "");

  // Prompt template fields (from PromptNode)
  const [promptText, setPromptText] = useState<string>(data.prompt || "");
  const [templateVars, setTemplateVars] = useState<string[]>(data.vars || []);

  // LLM configuration (using LLMListComponent like PromptNode)
  const llmListContainer = useRef<LLMListContainerRef>(null);
  const [llmItemsCurrState, setLLMItemsCurrState] = useState<LLMSpec[]>(
    data.llms || [],
  );

  // Preview modal
  const [showPreview, setShowPreview] = useState(false);
  const [previewPrompts, setPreviewPrompts] = useState<string[]>([]);

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

  // Callback for when LLM list changes (like PromptNode)
  const onLLMListItemsChange = useCallback(
    (items: LLMSpec[]) => {
      setLLMItemsCurrState(items);
      setDataPropsForNode(id, { llms: items });
    },
    [id, setDataPropsForNode],
  );

  // Callback for when prompt text changes
  const onPromptTextChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const newPrompt = e.target.value;
      setPromptText(newPrompt);
      setDataPropsForNode(id, { prompt: newPrompt });

      // Extract template variables from prompt
      const vars = extractBracketedSubstrings(newPrompt);
      setTemplateVars(vars);
      setDataPropsForNode(id, { vars });
    },
    [id, setDataPropsForNode],
  );

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
      prompt: promptText,
      vars: templateVars,
      llms: llmItemsCurrState,
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
    promptText,
    templateVars,
    llmItemsCurrState,
    setDataPropsForNode,
  ]);

  // Main optimization function
  const runOptimization = useCallback(async () => {
    const handleError = (msg: string, err?: any) => {
      console.error(msg, err);
      showAlert?.(msg);
      setStatus(Status.ERROR);
    };

    // 1) Check internal prompt template
    if (!promptText || promptText.trim() === "") {
      handleError(
        "No prompt template found. Please enter a prompt template in the editor.",
      );
      return;
    }

    // 2) Check LLM configuration
    if (!llmItemsCurrState || llmItemsCurrState.length === 0) {
      handleError("No LLM configured. Please add an LLM model.");
      return;
    }

    // 3) Pull test dataset from upstream (TabularDataNode or TextFieldsNode)
    let inputData: {
      input?: any[];
      label?: any[];
    } = {};
    try {
      inputData = pullInputData(["input", "label"], id) as {
        input?: any[];
        label?: any[];
      };
    } catch (error) {
      handleError(
        "No input data found. Connect TabularDataNode with 'input' and 'label' columns.",
        error,
      );
      return;
    }

    const inputColumn = inputData.input || [];
    const labelColumn = inputData.label || [];

    if (inputColumn.length === 0 || labelColumn.length === 0) {
      handleError(
        "No test dataset found. Connect TabularDataNode with 'input' and 'label' columns.",
      );
      return;
    }

    // Convert TabularDataNode format to test dataset
    // inputColumn/labelColumn are arrays of {text, metavars, associate_id}
    const testDataset = inputColumn.map((item: any, idx: number) => {
      const inputValue =
        typeof item === "object" && "text" in item ? item.text : item;
      const labelValue =
        typeof labelColumn[idx] === "object" && "text" in labelColumn[idx]
          ? labelColumn[idx].text
          : labelColumn[idx];

      return {
        text: inputValue,
        metavars: {
          label: labelValue,
        },
      };
    });

    setStatus(Status.LOADING);
    setJSONResponses([]);
    setOptimizationHistory([]);

    try {
      // Extract LLM configuration from first LLM in list
      const llm = llmItemsCurrState[0];
      const llmProvider = llm.name;
      const llmModel = llm.model || "";

      // Extract settings from LLM spec
      const llmParams: any = {};
      if (llm.settings) {
        llmParams.temperature = llm.settings.temperature ?? 0;
        llmParams.max_tokens = llm.settings.max_tokens ?? 10;
        // Add other settings as needed
        if (llm.settings.max_tokens !== undefined) {
          llmParams.max_tokens = llm.settings.max_tokens;
        }
        if (llm.settings.top_p !== undefined) {
          llmParams.top_p = llm.settings.top_p;
        }
      }

      const formData = new FormData();
      formData.append("method", "evolutionary_algorithm");

      // Use internal prompt template (not from PromptNode)
      formData.append("initial_prompts", JSON.stringify([promptText]));
      formData.append("test_dataset", JSON.stringify(testDataset));

      // LLM configuration from LLMListComponent
      formData.append("llm_provider", llmProvider);
      formData.append("llm_model", llmModel);
      formData.append("llm_params", JSON.stringify(llmParams));

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

  // Open inspector
  const openInspector = () => {
    if (jsonResponses.length > 0 && inspectorRef.current) {
      inspectorRef.current.trigger();
    }
  };

  // Preview function to show rendered prompts
  const showPromptPreview = useCallback(() => {
    try {
      const inputData = pullInputData(["input"], id);
      const inputColumn = inputData.input || [];

      if (!promptText || promptText.trim() === "") {
        showAlert?.("Enter a prompt template first");
        return;
      }

      if (inputColumn.length === 0) {
        showAlert?.("Connect TabularDataNode with 'input' column first");
        return;
      }

      // Render prompt template with first 3 test cases
      const previews = inputColumn.slice(0, 3).map((item: any) => {
        const inputValue =
          typeof item === "object" && "text" in item ? item.text : item;
        // Simple template variable replacement
        return promptText.replace(/\{input\}/g, inputValue);
      });

      setPreviewPrompts(previews);
      setShowPreview(true);
    } catch (error) {
      console.error("Preview error:", error);
      showAlert?.("Could not generate preview. Connect TabularDataNode first.");
    }
  }, [id, promptText, pullInputData, showAlert]);

  return (
    <BaseNode nodeId={id} classNames="optimizer-node">
      {/* Input handles for test data only (no prompts handle) */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        style={{ top: "50%" }}
      />
      <Handle
        type="target"
        position={Position.Left}
        id="label"
        style={{ top: "75%" }}
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
        {/* Prompt Template Editor */}
        <Divider label="Prompt Template" labelPosition="center" />
        <Textarea
          placeholder="Enter your prompt template with {input} variable..."
          value={promptText}
          onChange={onPromptTextChange}
          minRows={4}
          maxRows={8}
          autosize
          styles={{
            input: {
              fontSize: "11pt",
              fontFamily: "monospace",
            },
          }}
        />

        {/* Template Variables */}
        {templateVars.length > 0 && (
          <TemplateHooks
            vars={templateVars}
            nodeId={id}
            startY={0}
            position={Position.Left}
          />
        )}

        {/* LLM Configuration */}
        <Divider label="LLM Configuration" labelPosition="center" mt="sm" />
        <LLMListContainer
          ref={llmListContainer}
          initLLMItems={data.llms || []}
          onItemsChange={onLLMListItemsChange}
        />

        {/* Preview Button */}
        <Button
          size="xs"
          variant="light"
          leftIcon={<IconEye size={14} />}
          onClick={showPromptPreview}
          disabled={status === Status.LOADING}
        >
          Preview Rendered Prompts
        </Button>

        {/* Optimization Settings */}
        <Divider label="Optimization Settings" labelPosition="center" mt="sm" />

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

      {/* Preview Modal */}
      <Modal
        opened={showPreview}
        onClose={() => setShowPreview(false)}
        title="Rendered Prompt Preview"
        size="lg"
      >
        <Stack>
          <Text size="sm" c="dimmed">
            Showing first {previewPrompts.length} rendered prompts:
          </Text>
          {previewPrompts.map((prompt, idx) => (
            <Paper key={idx} p="sm" withBorder>
              <Text size="xs" fw={500} c="dimmed">
                Test Case {idx + 1}:
              </Text>
              <Code block mt="xs">
                {prompt}
              </Code>
            </Paper>
          ))}
        </Stack>
      </Modal>

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
