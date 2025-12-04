# Quick Fix for OptimizerNode.tsx

## Current Issues

The OptimizerNode has compilation errors because:
1. Old LLM variables (`llmProvider`, `llmModel`, etc.) are still referenced but were removed
2. TabularDataNode format not handled correctly
3. No preview functionality

## Immediate Fix: Revert to Working State + Minimal Changes

Since a full rewrite is complex, here's the quickest fix:

### Step 1: Revert the problematic changes

```bash
cd chainforge/react-server/src
# Revert OptimizerNode.tsx to use simple text inputs for LLM config
```

### Step 2: Keep the working backend changes

The Flask backend (chainforge/flask_app.py) changes are good and handle TabularDataNode format correctly.

### Step 3: Update OptimizerNode.tsx minimally

Just update the `runOptimization` function to properly handle TabularDataNode format:

```typescript
// In runOptimization function, replace the input data pulling:

// OLD:
let inputData: { prompts?: TemplateVarInfo[]; tabular?: any[] } = {};
try {
  inputData = pullInputData(["prompts", "tabular"], id) as {
    prompts?: TemplateVarInfo[];
    tabular?: any[];
  };
} catch (error) {
  handleError("No input data found.", error);
  return;
}

const promptsArr = inputData.prompts || [];
const testDataset = inputData.tabular || [];

// NEW:
let inputData: { prompts?: TemplateVarInfo[]; input?: any[]; label?: any[] } = {};
try {
  inputData = pullInputData(["prompts", "input", "label"], id) as {
    prompts?: TemplateVarInfo[];
    input?: any[];
    label?: any[];
  };
} catch (error) {
  handleError(
    "No input data found. Connect PromptNode and TabularDataNode with 'input' and 'label' columns.",
    error,
  );
  return;
}

const promptsArr = inputData.prompts || [];
const inputColumn = inputData.input || [];
const labelColumn = inputData.label || [];

if (promptsArr.length === 0) {
  handleError("No initial prompts found.");
  return;
}

if (inputColumn.length === 0 || labelColumn.length === 0) {
  handleError("No test dataset found. Connect TabularDataNode with 'input' and 'label' columns.");
  return;
}

// Convert TabularDataNode format to test dataset
// inputColumn/labelColumn are arrays of {text, metavars, associate_id}
const testDataset = inputColumn.map((item: any, idx: number) => {
  const inputValue = typeof item === 'object' && 'text' in item ? item.text : item;
  const labelValue = typeof labelColumn[idx] === 'object' && 'text' in labelColumn[idx]
    ? labelColumn[idx].text
    : labelColumn[idx];

  return {
    text: inputValue,
    metavars: {
      label: labelValue
    }
  };
});
```

### Step 4: Update input handles

```typescript
// Replace:
<Handle type="target" position={Position.Left} id="tabular" style={{ top: "70%" }} />

// With:
<Handle type="target" position={Position.Left} id="input" style={{ top: "50%" }} />
<Handle type="target" position={Position.Left} id="label" style={{ top: "75%" }} />
```

### Step 5: Keep simple LLM config (text inputs)

The current text input approach for LLM config works fine for now. Just ensure the state variables exist:
- llmProvider
- llmModel
- llmTemperature
- llmMaxTokens

## Alternative: Use the original OptimizerNode.tsx

If the current file is too broken, you can:

1. Git checkout the last working version of OptimizerNode.tsx
2. Only apply these minimal changes:
   - Update input pulling to use "input" and "label" handles
   - Add input handles for "input" and "label"
   - Keep the simple LLM text input configuration

The Flask backend will handle the TabularDataNode format conversion automatically.

## User Workflow with This Fix

1. **TabularDataNode**: Create with columns "input" and "label"
2. **PromptNode**: Create template with `{input}` variable
3. **OptimizerNode**:
   - Connect PromptNode → "prompts"
   - Connect TabularDataNode "input" column → "input"
   - Connect TabularDataNode "label" column → "label"
   - Configure LLM (Provider, Model, Temperature, MaxTokens)
   - Run optimization

The backend will:
- Receive test data in TabularDataNode format
- Convert it to `{input, label}` format
- Render templates internally
- Call LLMs
- Calculate fitness
- Return best prompt

## Files Status

✅ **Working**:
- `chainforge/flask_app.py` - Handles TabularDataNode format
- `chainforge/optimizers/evolutionary.py` - Async support

⚠️ **Broken**:
- `chainforge/react-server/src/OptimizerNode.tsx` - Has TypeScript errors

🔧 **Fix Needed**:
- Revert OptimizerNode.tsx or apply minimal changes above
