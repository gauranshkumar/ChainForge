# Critical Fixes Needed for Optimizer Implementation

## Issues Identified

1. **TabularDataNode data format**: Returns `[{text, metavars, associate_id}]` not `[{input, label}]`
2. **LLM Configuration**: Should use ChainForge's `LLMListComponent` instead of text fields
3. **Missing Preview**: No way to see rendered prompts before optimization

## Fix 1: TabularDataNode Format (✅ DONE in Flask)

**File**: `chainforge/flask_app.py` (lines 2012-2032)

The Flask backend now correctly handles TabularDataNode format:
```python
# Converts from: [{text: "input_value", metavars: {label: "label_value"}}]
# To: [{input: "input_value", label: "label_value"}]
```

## Fix 2: OptimizerNode UI - Use LLMListComponent

**File**: `chainforge/react-server/src/OptimizerNode.tsx`

### Changes Needed:

#### 1. Update imports (DONE):
```typescript
import { LLMListContainer, LLMListContainerRef } from "./LLMListComponent";
import { LLMSpec } from "./backend/typing";
```

#### 2. Update data interface (DONE):
```typescript
interface OptimizerNodeData {
  // ... existing fields ...
  llms?: LLMSpec[];  // Replace llm_provider, llm_model, etc.
  refresh?: boolean;
}
```

#### 3. Replace state variables (PARTIALLY DONE - need to remove old code):

**Remove these:**
```typescript
const [llmProvider, setLlmProvider] = useState(data.llm_provider || "OpenAI");
const [llmModel, setLlmModel] = useState(data.llm_model || "gpt-4");
const [llmTemperature, setLlmTemperature] = useState(data.llm_temperature || 0);
const [llmMaxTokens, setLlmMaxTokens] = useState(data.llm_max_tokens || 10);
```

**Add these (DONE):**
```typescript
const llmListContainer = useRef<LLMListContainerRef>(null);
const [llmItemsCurrState, setLLMItemsCurrState] = useState<LLMSpec[]>(data.llms || []);
const [showPreview, setShowPreview] = useState(false);
const [previewPrompts, setPreviewPrompts] = useState<string[]>([]);
```

#### 4. Add LLM items change handler:
```typescript
const onLLMListItemsChange = useCallback((items: LLMSpec[]) => {
  setLLMItemsCurrState(items);
  setDataPropsForNode(id, { llms: items });
}, [id, setDataPropsForNode]);
```

#### 5. Update settings persistence (remove llm_provider, llm_model, etc.):
```typescript
useEffect(() => {
  setDataPropsForNode(id, {
    population_size: populationSize,
    // ... other settings ...
    llms: llmItemsCurrState,  // Save LLM list instead
  });
}, [
  id,
  populationSize,
  // ... other deps ...
  llmItemsCurrState,  // Add this dependency
  setDataPropsForNode,
]);
```

#### 6. Update runOptimization to use LLM list:
```typescript
const runOptimization = useCallback(async () => {
  // ...

  // Check if LLM is configured
  if (!llmItemsCurrState || llmItemsCurrState.length === 0) {
    handleError("No LLM configured. Please add an LLM model.");
    return;
  }

  const llm = llmItemsCurrState[0]; // Use first LLM
  const llmProvider = llm.name;
  const llmModel = llm.model || "";

  // Extract settings from LLM spec
  const llmParams: any = {};
  if (llm.settings) {
    llmParams.temperature = llm.settings.temperature ?? 0;
    llmParams.max_tokens = llm.settings.max_tokens ?? 10;
    // Add other settings as needed
  }

  // ...

  formData.append("llm_provider", llmProvider);
  formData.append("llm_model", llmModel);
  formData.append("llm_params", JSON.stringify(llmParams));

  // ...
}, [
  id,
  llmItemsCurrState,  // Add to dependencies
  // ... other deps ...
]);
```

#### 7. Add tabular data handling:
```typescript
// In runOptimization:

// Pull data from TabularDataNode - it comes as array of {text, metavars, associate_id}
const inputData = pullInputData(["prompts", "input", "label"], id);

const promptsArr = inputData.prompts || [];
const inputColumn = inputData.input || [];  // Pull from "input" column
const labelColumn = inputData.label || [];  // Pull from "label" column

if (promptsArr.length === 0) {
  handleError("No initial prompts found.");
  return;
}

if (inputColumn.length === 0 || labelColumn.length === 0) {
  handleError("No test dataset found. Connect TabularDataNode with 'input' and 'label' columns.");
  return;
}

// Convert to test dataset format
const testDataset = inputColumn.map((item: any, idx: number) => ({
  input: typeof item === 'object' ? item.text : item,
  label: typeof labelColumn[idx] === 'object' ? labelColumn[idx].text : labelColumn[idx]
}));

// Send to backend
formData.append("initial_prompts", JSON.stringify(promptsArr.map((p) => p.text)));
formData.append("test_dataset", JSON.stringify(testDataset));
```

#### 8. Add preview function:
```typescript
const showPromptPreview = useCallback(() => {
  try {
    const inputData = pullInputData(["prompts", "input"], id);
    const promptsArr = inputData.prompts || [];
    const inputColumn = inputData.input || [];

    if (promptsArr.length === 0 || inputColumn.length === 0) {
      showAlert?.("Connect PromptNode and TabularDataNode first");
      return;
    }

    // Render first prompt with first 3 test cases
    const template = promptsArr[0].text;
    const previews = inputColumn.slice(0, 3).map((item: any) => {
      const inputValue = typeof item === 'object' ? item.text : item;
      return template.replace(/\{input\}/g, inputValue);
    });

    setPreviewPrompts(previews);
    setShowPreview(true);
  } catch (error) {
    console.error("Preview error:", error);
  }
}, [id, pullInputData, showAlert]);
```

#### 9. Replace LLM Configuration UI section:

**Remove:**
```typescript
<Accordion.Item value="llm">
  <Accordion.Control>LLM Configuration</Accordion.Control>
  <Accordion.Panel>
    <Stack spacing="xs">
      <TextInput label="Provider" value={llmProvider} onChange={...} />
      <TextInput label="Model" value={llmModel} onChange={...} />
      <NumberInput label="Temperature" value={llmTemperature} ... />
      <NumberInput label="Max Tokens" value={llmMaxTokens} ... />
    </Stack>
  </Accordion.Panel>
</Accordion.Item>
```

**Add:**
```typescript
<Accordion.Item value="llm">
  <Accordion.Control>LLM Configuration</Accordion.Control>
  <Accordion.Panel>
    <LLMListContainer
      ref={llmListContainer}
      initLLMItems={data.llms}
      onItemsChange={onLLMListItemsChange}
    />
  </Accordion.Panel>
</Accordion.Item>
```

#### 10. Add preview button and modal:
```typescript
// In the UI, before the Run button:
<Button
  size="xs"
  variant="light"
  leftIcon={<IconEye size={14} />}
  onClick={showPromptPreview}
  disabled={status === Status.LOADING}
>
  Preview Prompts
</Button>

// Add preview modal at the end:
{showPreview && (
  <Modal
    opened={showPreview}
    onClose={() => setShowPreview(false)}
    title="Rendered Prompt Preview"
    size="lg"
  >
    <Stack>
      <Text size="sm" color="dimmed">
        Showing first 3 rendered prompts:
      </Text>
      {previewPrompts.map((prompt, idx) => (
        <Paper key={idx} p="sm" withBorder>
          <Text size="xs" weight={500} color="dimmed">Test Case {idx + 1}:</Text>
          <Code block mt="xs">{prompt}</Code>
        </Paper>
      ))}
    </Stack>
  </Modal>
)}
```

## Fix 3: TabularDataNode Connection

### User Workflow:

1. **Create TabularDataNode** with 2 columns:
   - Column 1: Header = "input" (test inputs)
   - Column 2: Header = "label" (ground truth labels)

2. **Create PromptNode** with template:
   ```
   Classify the sentiment: {input}

   [DATA]
   Example: "Great!" → positive
   Example: "Bad" → negative
   [/DATA]

   Answer:
   ```

3. **Connect to OptimizerNode**:
   - PromptNode → OptimizerNode `prompts` handle
   - TabularDataNode "input" column → OptimizerNode `input` handle
   - TabularDataNode "label" column → OptimizerNode `label` handle

4. **Configure OptimizerNode**:
   - Add LLM (e.g., OpenAI gpt-4)
   - Set temperature to 0
   - Set max_tokens to 10
   - Set population, generations, etc.

5. **Preview** (click Preview button):
   - See rendered prompts with actual test data

6. **Run Optimization**:
   - Optimizer internally renders templates
   - Calls LLM for each test case
   - Calculates fitness
   - Evolves population

## Summary of Files to Modify

### ✅ Already Fixed:
- `chainforge/flask_app.py` - TabularDataNode format handling
- `chainforge/optimizers/evolutionary.py` - Async evaluation support

### 🔧 Needs Fixing:
- `chainforge/react-server/src/OptimizerNode.tsx` - Major refactor needed:
  - Remove old LLM state variables (lines 101-106)
  - Add LLM list handler
  - Update runOptimization (lines 169-342)
  - Replace LLM UI section (lines 505-560)
  - Add preview functionality
  - Update input handles to accept "input" and "label" separately

### 📝 New Input Handles Needed:

Current:
```typescript
<Handle type="target" position={Position.Left} id="prompts" style={{ top: "30%" }} />
<Handle type="target" position={Position.Left} id="tabular" style={{ top: "70%" }} />
```

Should be:
```typescript
<Handle type="target" position={Position.Left} id="prompts" style={{ top: "25%" }} />
<Handle type="target" position={Position.Left} id="input" style={{ top: "50%" }} />
<Handle type="target" position={Position.Left} id="label" style={{ top: "75%" }} />
```

## Testing Checklist

1. ✅ Flask correctly parses TabularDataNode format
2. ⬜ OptimizerNode accepts LLM from LLMListComponent
3. ⬜ Preview shows rendered prompts
4. ⬜ Optimization runs with internal LLM calls
5. ⬜ Data sections preserved during evolution
6. ⬜ Best prompt returned with fitness score

## Next Steps

1. Complete OptimizerNode.tsx refactor (see detailed changes above)
2. Test with sample data
3. Verify all three requirements:
   - ✅ TabularDataNode format handling
   - ⬜ LLM provider selector
   - ⬜ Rendered prompt preview
