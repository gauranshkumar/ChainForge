# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ChainForge is a visual programming environment for prompt engineering and LLM evaluation. It combines a **React frontend** (using ReactFlow for node-based visual programming) with a **Flask backend** that orchestrates LLM API calls, caching, and data processing.

## Development Commands

### Python Backend

```bash
# Install core dependencies
pip install -e .

# Install with RAG (Retrieval-Augmented Generation) support
pip install -e .[rag]

# Install with Optimizer support (Evolutionary Algorithms)
pip install -e .[optimizer]

# Install with all optional features
pip install -e .[all]

# Install spaCy language model (required for optimizer crossover)
python -m spacy download en_core_web_sm

# Run the ChainForge server
chainforge serve

# Run tests
pytest

# Run specific test file
pytest tests/test_chunking.py
```

### React Frontend

```bash
cd chainforge/react-server

# Install dependencies
npm install

# Development server with linting and formatting
npm start

# Build production bundle
npm build

# Run tests
npm test

# Lint and format only
npm run clean
```

### Docker

```bash
# CPU version (multi-architecture: AMD64 + ARM64)
docker-compose up -d

# GPU version (AMD64 only, requires NVIDIA Docker runtime)
docker-compose -f docker-compose.gpu.yml up -d

# Build locally
docker build -t chainforge:cpu .
docker build -f Dockerfile.gpu -t chainforge:gpu .

# Access at http://localhost:8000
```

## Architecture

### Backend Structure (`/chainforge/`)

**flask_app.py** (~2100 lines): Central Flask server containing:
- Routes for executing Python evaluators (`/executepy`)
- LLM response caching and batch processing
- RAG endpoints (`/chunk`, `/retrieve`, `/rerank`)
- Optimizer endpoint (`/optimize`) for evolutionary prompt optimization
- Flow save/load with optional encryption
- Media upload/download handlers

**providers/**: Plugin system for LLM providers
- Uses `@provider` decorator to register custom providers
- `protocol.py`: Defines provider registry and decorators
- Supports categories: model, retriever, chunker
- Providers are dynamically loaded from user scripts

**rag/**: Retrieval-Augmented Generation modules
- `chunkers.py`: Text splitting strategies (tiktoken, semantic, HuggingFace)
- `retrievers.py`: Search algorithms (BM25, TF-IDF, semantic similarity)
- `rerankers.py`: Result ranking and fusion methods
- `embeddings.py`: Embedding generation
- `vector_stores.py`: LanceDB and FAISS vector database abstraction

**optimizers/**: Evolutionary algorithm-based prompt optimization
- `protocol.py`: Optimizer registry and decorator pattern
- `evolutionary.py`: EA implementation with:
  - Selection methods: Tournament, Roulette Wheel
  - Crossover: Semantic chunking using spaCy
  - Mutation: Neo4j taxonomy-based or simple word-level
  - Fitness metrics: MCC, Balanced Accuracy
- `utils.py`: Fitness calculation and selection utilities

**security/**: Password-based encryption for flows and settings

### Frontend Structure (`/chainforge/react-server/src/`)

**store.tsx**: Zustand-based global state managing:
- ReactFlow graph (nodes and edges)
- LLM configurations and API keys
- Cached responses and evaluations
- UI state (modals, selections)

**Node System** (~71 node types in `/components/`):
- `BaseNode.tsx`: Wrapper providing context menus (duplicate, delete, favorite)
- Input nodes: `TextFieldsNode`, `PromptNode`, `UploadNode`, `MediaNode`
- Processing: `ChunkNode`, `RetrievalNode`, `RerankNode`, `OptimizerNode`
- Evaluation: `CodeEvaluatorNode`, `LLMEvalNode`, `SimpleEvalNode`
- Output: `TabularDataNode`, `VisNode`, `InspectNode`

**backend/** utilities:
- `backend.ts`: Core API communication with Flask
- `models.ts`: LLM provider wrappers
- `cache.ts`: Browser storage cache
- `template.ts`: Prompt templating with `{variable}` syntax

### Data Flow

1. User creates visual flow in React (nodes + edges)
2. User runs node → POST to Flask (`/executepy`, `/retrieve`, etc.)
3. Flask processes request:
   - Checks response cache
   - Routes to appropriate provider via `ProviderRegistry`
   - Calls external LLM APIs or local RAG
4. Responses cached and returned to React
5. React updates store → UI renders results
6. User can chain evaluations or save flow

### Response Object Format

All nodes pass standardized response objects:
```typescript
{
  text: string              // Response content
  prompt: string            // Original prompt
  vars: {}                  // Template variables used
  metavars: {}              // Metadata (LLM name, model, timestamps)
  eval_res?: {              // Evaluation results (optional)
    items: any[]            // Scores/evaluations
    dtype: string           // Data type (Numeric, Categorical, etc.)
  }
}
```

### LLM Provider System

Providers use decorator registration:
```python
@provider(
    name="MyProvider",
    emoji="🚀",
    models=["model1", "model2"],
    settings_schema={...},    # JSON Schema for react-jsonschema-form
    category="model"          # model | retriever | chunker
)
def my_provider(prompt, model, chat_history=None, **kwargs):
    # Implementation
    return response_text
```

Built-in providers: OpenAI, Anthropic Claude, HuggingFace, Google Gemini, Azure OpenAI, AWS Bedrock, Together, DeepSeek, Ollama.

## Key Design Decisions

1. **No Code Sandboxing**: User Python code in evaluators runs directly in Flask process (trust model: self-hosted)
2. **Stateless Backend**: All state in React store; Flask is request/response only
3. **File-Based Persistence**: Flows saved as JSON (optionally encrypted) to local filesystem
4. **Protocol-Based Extension**: Providers implement callables, not inheritance
5. **Metadata Propagation**: All responses tagged with provenance (LLM, settings, timestamps)

## Code Style

### Frontend
- Uses ESLint with semistandard config
- Prettier for formatting (automatically runs before build/start)
- TypeScript for type safety
- React functional components with hooks

### Backend
- Python 3.10+ required
- Flask with async support for concurrent LLM calls
- Uses `platformdirs` for cross-platform data directories
- Response caching via SHA hashing

## Testing

- Tests located in `/tests/`
- Current tests focus on RAG functionality (chunking, retrieval, reranking, vector stores)
- Run with: `pytest` or `pytest tests/test_chunking.py`
- GitHub Actions runs validation on Python 3.10, 3.11, 3.12 across Ubuntu, Windows, macOS

## Important Files

| File | Purpose | Lines |
|------|---------|-------|
| `chainforge/flask_app.py` | Backend API endpoints, LLM orchestration | ~2000 |
| `chainforge/react-server/src/store.tsx` | Global state management | ~1000 |
| `chainforge/providers/protocol.py` | Provider registration system | 222 |
| `chainforge/react-server/src/App.tsx` | Main React app, node canvas | ~1500 |
| `chainforge/react-server/src/backend/backend.ts` | API communication layer | ~2000 |

## Docker Build System

ChainForge uses multi-stage Docker builds with parallel architecture builds:

- **CPU images**: Multi-arch (AMD64 + ARM64), tagged as `latest`, `cpu`
- **GPU images**: AMD64 only with CUDA 12.1, tagged as `gpu`
- **CI/CD**: GitHub Actions builds on PRs, branch pushes, and version tags
- **Storage optimization**: No QEMU, no GitHub cache, aggressive disk cleanup for GPU builds

See `DOCKER.md` for detailed Docker documentation.

## Node Development

When creating new nodes:
1. Create component in `chainforge/react-server/src/components/`
2. Extend `BaseNode` for context menu support
3. Define input/output handles using ReactFlow Handle components
4. Implement `data` prop interface with node-specific fields
5. Handle data flow through `onConnect` callbacks
6. Register in `nodeTypes` mapping in `App.tsx`

## RAG Pipeline

Three-stage pipeline:
1. **Chunking** (ChunkNode): Text → List[chunks]
2. **Retrieval** (RetrievalNode): (Chunks, Queries) → Ranked results
3. **Reranking** (RerankNode): Results → Better ranked results

Each stage is extensible via registry pattern (`ChunkingMethodRegistry`, `RetrievalMethodRegistry`, `RerankingMethodRegistry`).

## Optimizer System

**OptimizerNode** uses evolutionary algorithms to optimize prompts for text classification tasks:

**Architecture:**
- Registry pattern (`OptimizerRegistry`) similar to RAG modules
- Endpoint: `/optimize` (POST request with FormData)
- Inputs: Initial prompts, evaluation data, optimizer settings
- Outputs: Best prompt, fitness scores, generation history

**Evolutionary Algorithm Features:**
1. **Selection Methods:**
   - Tournament selection (default)
   - Roulette wheel selection

2. **Crossover:**
   - Semantic chunking using spaCy
   - Sentence-level recombination
   - Fallback to simple period-based splitting

3. **Mutation:**
   - Neo4j taxonomy-based (requires Neo4j connection)
   - Simple word-level mutation (fallback)

4. **Fitness Metrics:**
   - Matthews Correlation Coefficient (MCC)
   - Balanced Accuracy Score

**Usage:**
- Connect PromptNode → OptimizerNode for initial prompts
- Connect EvaluatorNode → OptimizerNode for evaluation data
- Configure population size, generations, mutation/crossover rates
- Optional: Configure Neo4j for taxonomy-based mutation
- Run optimization to get best prompt

**Configuration Parameters:**
- `population_size`: Number of individuals (default: 10)
- `num_generations`: Evolutionary generations (default: 5)
- `mutation_rate`: Probability of mutation (default: 0.3)
- `crossover_rate`: Probability of crossover (default: 0.7)
- `selection_method`: 'tournament' or 'roulette' (default: 'tournament')
- `tournament_size`: Tournament size if using tournament selection (default: 3)
- `fitness_metric`: 'mcc' or 'balanced_accuracy' (default: 'mcc')
- `elitism_count`: Number of elite individuals to preserve (default: 2)
- `neo4j_uri`, `neo4j_user`, `neo4j_password`: Optional Neo4j connection

**Neo4j Graph Schema** (for mutation):
```cypher
(PromptTemplate)-[:BELONGS_TO]->(Category)
(PromptTemplate)-[:SIMILAR_TO]->(PromptTemplate)
```

Each `PromptTemplate` node should have a `text` property containing the template.

## Environment Variables

Optional API keys can be set via environment variables (auto-loaded by Flask):
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`
- `COHERE_API_KEY`
- `DEEPSEEK_API_KEY`
- `HUGGINGFACE_API_KEY`

Alternatively, set in UI via Settings icon (top-right).
