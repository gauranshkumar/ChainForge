---
theme: default
# background: https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1920
class: intro
highlighter: shiki
lineNumbers: false
info: |
  ## Prompt Evolution Lab
  Towards Systematic Prompt Optimisation for Real Tasks
drawings:
  persist: false
transition: slide-left
title: Prompt Evolution Lab
mdc: true

---

# Prompt Evolution Lab

#### Towards Systematic Prompt Optimisation for Real Tasks

<div class="pt-12">
  <span class="text-xl">
    Gauransh Kumar & Vennila Sooben
  </span>
  <br />
  <span class="text-gray-400">IFT 6076</span>
</div>

---
layout: center
---

# The Challenge

<v-clicks>

- Manual prompt engineering is **time-consuming**
- Trial-and-error lacks **systematic approach**
- Hard to optimize for **real classification tasks**

</v-clicks>

<div v-click class="text-center mt-8 text-2xl font-semibold text-emerald-400 opacity-90">
Solution: Evolutionary Algorithms
</div>

---
layout: two-cols
---

# Evolutionary Algorithms

<v-clicks>

- Inspired by **natural selection**
- Population-based optimization
- Iterative improvement
- Genetic operators

</v-clicks>

::right::

```mermaid {scale: 0.6}
graph TD
    A[Initial Population] --> B[Evaluate Fitness]
    B --> C{Converged?}
    C -->|No| D[Selection]
    D --> E[Crossover]
    E --> F[Mutation]
    F --> G[New Generation]
    G --> B
    C -->|Yes| H[Best Prompt]

    style A fill:#86efac,stroke:#4ade80
    style H fill:#fde68a,stroke:#fbbf24
    style D fill:#93c5fd,stroke:#60a5fa
    style E fill:#c4b5fd,stroke:#a78bfa
    style F fill:#fca5a5,stroke:#f87171
```

---
layout: center
---

# System Architecture

```mermaid {scale: 0.5}
graph LR
    A[Input: Initial Prompts] --> B[Optimizer Node]
    C[Evaluation Data] --> B
    B --> D[Registry]
    D --> E[EA Engine]
    E --> F[Selection]
    E --> G[Crossover]
    E --> H[Mutation]
    F --> I[Tournament/Roulette]
    G --> J[Semantic Chunking]
    H --> K[Neo4j Taxonomy]
    I --> L[Next Generation]
    J --> L
    K --> L
    L --> M{Done?}
    M -->|No| E
    M -->|Yes| N[Best Prompt]

    style B fill:#86efac,stroke:#4ade80
    style D fill:#93c5fd,stroke:#60a5fa
    style E fill:#fde68a,stroke:#fbbf24
    style N fill:#c4b5fd,stroke:#a78bfa
```

---

# Selection Operators

<div class="grid grid-cols-2 gap-8">

<div v-click>

## Tournament Selection

- Select k random individuals
- Choose best among them
- Higher selection pressure
- **Default method**

</div>
<div v-click>

```mermaid {scale: 0.6}
graph TD
    A[Population] --> B[Random k=3]
    B --> C[Compare Fitness]
    C --> D[Winner]

    style D fill:#86efac,stroke:#4ade80
```

</div>

</div>

---

# Novel Feature: Semantic Crossover

<v-clicks>

- Uses **spaCy NLP** for sentence detection
- Sentence-level recombination
- Preserves semantic meaning
- Fallback: period-based splitting

</v-clicks>

```mermaid {scale: 0.7}
graph LR
    A[Parent 1: S1.S2.S3] --> C[spaCy Parse]
    B[Parent 2: S4.S5.S6] --> D[spaCy Parse]
    C --> E[Crossover Point]
    D --> E
    E --> F[Child 1: S1.S2.S5.S6]
    E --> G[Child 2: S4.S3]

    style F fill:#86efac,stroke:#4ade80
    style G fill:#93c5fd,stroke:#60a5fa
```

<div v-click class="text-center mt-4 text-sm text-gray-400">
Semantic chunks ensure coherent offspring prompts
</div>

---

# Novel Feature: Taxonomy-Based Mutation

<div class="grid grid-cols-2 gap-4">

<div>

<v-clicks>

- Connects to **Neo4j/Memgraph**
- Pattern taxonomy database
- Cross-category mutations
- Ensures diversity

</v-clicks>

<div v-click class="mt-4 text-xs">

**Graph Schema:**
```
(Pattern {label: "text"})
  ↓ BELONGS_TO
(SubCategory {name: "X"})
  ↓ BELONGS_TO
(Category {name: "Y"})
```

</div>

</div>

<div>

```mermaid {scale: 0.5}
graph TD
    A[Prompt] --> B[Identify Category]
    B --> C{Neo4j Connected?}
    C -->|Yes| D[Query Different Category]
    C -->|No| E[Simple Word Mutation]
    D --> F[Select Template]
    F --> G[Replace Sentence]
    E --> G
    G --> H[Mutated Prompt]

    style D fill:#c4b5fd,stroke:#a78bfa
    style E fill:#fde68a,stroke:#fbbf24
    style H fill:#86efac,stroke:#4ade80
```

</div>

</div>

---

# Novel Feature: Data Preservation

<v-clicks>

- Protects examples during evolution
- Detects **`[DATA]...[/DATA]`** tags
- Preserves code blocks **` ```...``` `**
- Keeps example lines intact

</v-clicks>

<div v-click class="mt-8">

```mermaid {scale: 0.65}
graph LR
    A[Original Prompt] --> B[Split Segments]
    B --> C[Mutable Text]
    B --> D[Data Sections]
    C --> E[Apply Operators]
    D --> F[Preserve]
    E --> G[Reconstruct]
    F --> G
    G --> H[New Prompt]

    style C fill:#fca5a5,stroke:#f87171
    style D fill:#86efac,stroke:#4ade80
    style H fill:#c4b5fd,stroke:#a78bfa
```

</div>

<div v-click class="text-center mt-4 text-sm text-gray-400">
Only instructions evolve, examples stay constant
</div>

---

# Fitness Metrics

<div class="grid grid-cols-2 gap-8 mt-8">

<div v-click>

## Matthews Correlation Coefficient

- Range: **[-1, 1]**
- Handles imbalanced classes
- **Default metric**
- Robust for binary/multiclass

$$
MCC = \frac{TP \times TN - FP \times FN}{\sqrt{(TP+FP)(TP+FN)(TN+FP)(TN+FN)}}
$$

</div>

<div v-click>

## Balanced Accuracy

- Average of per-class recall
- Range: **[0, 1]**
- Alternative metric
- Intuitive interpretation

$$
BA = \frac{1}{C}\sum_{i=1}^{C} \frac{TP_i}{TP_i + FN_i}
$$

</div>

</div>

<div v-click class="text-center mt-8 text-lg text-slate-400">
Both metrics ensure fair evaluation across imbalanced datasets
</div>

---

# Complete Workflow

<div class="grid grid-rows-2 gap-8">

<div>

## Input & Evaluation

```mermaid {scale: 0.7}
graph LR
    A[Initial<br/>Prompts] --> B[Optimizer<br/>Node]
    C[Eval<br/>Data] --> B
    B --> D[Evaluate<br/>Population]
    D --> E[Calculate<br/>Fitness]

    style B fill:#86efac,stroke:#4ade80
    style E fill:#93c5fd,stroke:#60a5fa
```
</div>

<div>

## Evolution Loop

```mermaid {scale: 0.7}
graph LR
    F[Keep<br/>Elite] --> G[Selection]
    G --> H[Crossover]
    H --> I[Mutation]
    I --> J{Max<br/>Gen?}
    J -->|No| F
    J -->|Yes| K[Best<br/>Prompt]

    style H fill:#c4b5fd,stroke:#a78bfa
    style I fill:#fca5a5,stroke:#f87171
    style K fill:#fde68a,stroke:#fbbf24
```

</div>

</div>

---
layout: center
class: text-center
---

# Key Innovations

<v-clicks>

<div class="text-3xl mb-4">🧬 Semantic sentence-level crossover</div>

<div class="text-3xl mb-4">🗄️ Taxonomy-driven mutation with Neo4j</div>

<div class="text-3xl mb-4">🛡️ Intelligent data preservation</div>

<div class="text-3xl mb-4">📊 Robust fitness metrics for real tasks</div>

</v-clicks>

---
layout: center
class: text-center
---

# Thank You

## Questions?

<div class="mt-12">
  <div class="text-xl">Gauransh Kumar & Vennila Sooben</div>
  <div class="mt-4 text-gray-400">Prompt Evolution Lab</div>
</div>
