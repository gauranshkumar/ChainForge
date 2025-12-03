# Memgraph Integration for Prompt Optimization

This document describes how the ChainForge optimizer integrates with Memgraph for taxonomy-based mutation.

## Overview

The evolutionary algorithm optimizer uses Memgraph to perform intelligent prompt mutations by fetching semantically similar templates from a prompt taxonomy graph database.

## Graph Schema

The Memgraph database should contain Pattern nodes organized by categories:

### Schema Structure

```cypher
(Pattern {label: "template text"})-[:BELONGS_TO]->(SubCategory {name: "subcategory"})
(SubCategory)-[:BELONGS_TO]->(Category {name: "category"})
```

Or simpler version:
```cypher
(Pattern {label: "template text"})-[:BELONGS_TO]->(Category {name: "category"})
```

### Key Properties

- **Pattern.label**: Contains the prompt template text
- **SubCategory.name**: Name of the subcategory
- **Category.name**: Name of the top-level category

## How Mutation Works

### Step 1: Identify Current Category

When mutating a prompt, the algorithm first tries to identify which category the current prompt belongs to:

```cypher
MATCH (p:Pattern)
WHERE p.label CONTAINS $search_term
OPTIONAL MATCH (p)-[:BELONGS_TO]->(sc:SubCategory)
OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
OPTIONAL MATCH (sc)-[:BELONGS_TO]->(c2:Category)
RETURN sc.name as subcategory,
       COALESCE(c.name, c2.name) as category
LIMIT 1
```

### Step 2: Fetch Templates from Different Categories

To ensure **diversity** in mutation, the algorithm fetches templates from DIFFERENT categories:

#### Query 1: Different SubCategories
```cypher
MATCH (p:Pattern)-[:BELONGS_TO]->(sc:SubCategory)
WHERE sc.name <> $current_subcategory AND p.label IS NOT NULL
RETURN DISTINCT p.label as template
LIMIT 10
```

#### Query 2: Different Categories
```cypher
MATCH (p:Pattern)-[:BELONGS_TO*1..2]->(c:Category)
WHERE c.name <> $current_category AND p.label IS NOT NULL
RETURN DISTINCT p.label as template
LIMIT 10
```

#### Query 3: Fallback (any patterns)
```cypher
MATCH (p:Pattern)
WHERE p.label IS NOT NULL
RETURN p.label as template
LIMIT 10
```

### Step 3: Replace Sentence

Once a template is selected:
1. The prompt is split into sentences (using spaCy or simple period-based splitting)
2. A random sentence is replaced with the selected template
3. The mutated prompt is returned

## Configuration

### Connection Settings

Default connection to Memgraph:
- **URI**: `bolt://localhost:7688`
- **Auth**: None (Memgraph typically doesn't require authentication)

### In OptimizerNode UI

Configure Memgraph connection in the "Neo4j Mutation" accordion:
- **Neo4j URI**: `bolt://localhost:7688`
- **Username**: (leave empty for Memgraph)
- **Password**: (leave empty for Memgraph)

### Programmatic Configuration

```python
neo4j_connection = {
    "uri": "bolt://localhost:7688",
    "user": "",  # Empty for Memgraph
    "password": ""  # Empty for Memgraph
}
```

## Testing

### Test Script

Run the test script to verify your Memgraph setup:

```bash
python chainforge/optimizers/test_memgraph_query.py
```

This will:
1. Connect to Memgraph
2. Count Pattern nodes
3. Sample Pattern templates
4. Test category/subcategory relationships
5. Verify cross-category queries work

### Schema Inspector

Inspect your Memgraph schema:

```bash
python chainforge/optimizers/schema_inspector.py
```

This shows:
- All node labels
- Relationship types
- Sample nodes and properties
- Relationship patterns
- Node counts

## Example Graph Setup

### Sample Data

Here's an example of how to set up a simple taxonomy in Memgraph:

```cypher
// Create Categories
CREATE (sent:Category {name: "Sentiment Analysis"})
CREATE (sum:Category {name: "Summarization"})
CREATE (qa:Category {name: "Question Answering"})

// Create SubCategories
CREATE (pos:SubCategory {name: "Positive Detection"})
CREATE (neg:SubCategory {name: "Negative Detection"})
CREATE (brief:SubCategory {name: "Brief Summary"})
CREATE (detailed:SubCategory {name: "Detailed Summary"})

// Link SubCategories to Categories
CREATE (pos)-[:BELONGS_TO]->(sent)
CREATE (neg)-[:BELONGS_TO]->(sent)
CREATE (brief)-[:BELONGS_TO]->(sum)
CREATE (detailed)-[:BELONGS_TO]->(sum)

// Create Pattern nodes
CREATE (p1:Pattern {label: "Classify the sentiment as positive or negative"})
CREATE (p2:Pattern {label: "Determine if the text expresses positive or negative emotions"})
CREATE (p3:Pattern {label: "Identify whether the review is favorable or unfavorable"})
CREATE (p4:Pattern {label: "Summarize the key points in 2-3 sentences"})
CREATE (p5:Pattern {label: "Provide a brief overview of the main ideas"})

// Link Patterns to SubCategories
CREATE (p1)-[:BELONGS_TO]->(pos)
CREATE (p2)-[:BELONGS_TO]->(pos)
CREATE (p3)-[:BELONGS_TO]->(neg)
CREATE (p4)-[:BELONGS_TO]->(brief)
CREATE (p5)-[:BELONGS_TO]->(brief)
```

## Benefits

### Why Cross-Category Mutation?

1. **Diversity**: Fetching from different categories prevents local optima
2. **Exploration**: Introduces novel prompt structures from unrelated domains
3. **Innovation**: Cross-pollination of ideas from different task types
4. **Robustness**: Prevents over-fitting to a single prompt style

### Fallback Mechanism

If Memgraph is unavailable or queries fail:
- Falls back to **simple word-level mutation**
- Randomly swaps adjacent words
- Ensures the optimizer continues running

## Troubleshooting

### Connection Issues

**Error**: "Unable to connect to Memgraph"

**Solutions**:
1. Check if Memgraph is running:
   ```bash
   docker ps | grep memgraph
   ```
2. Start Memgraph if not running:
   ```bash
   docker run -p 7688:7687 memgraph/memgraph
   ```
3. Verify the URI is correct: `bolt://localhost:7688`

### Empty Results

**Error**: No templates returned from queries

**Solutions**:
1. Check if Pattern nodes exist:
   ```cypher
   MATCH (p:Pattern) RETURN count(p)
   ```
2. Verify Pattern nodes have `label` property:
   ```cypher
   MATCH (p:Pattern) WHERE p.label IS NOT NULL RETURN p.label LIMIT 5
   ```
3. Check relationships:
   ```cypher
   MATCH (p:Pattern)-[r]->(n) RETURN type(r), labels(n) LIMIT 10
   ```

### Performance

For large graphs (>10,000 patterns):
- Add indexes on Pattern.label and Category/SubCategory names
- Adjust LIMIT values in queries
- Consider caching frequently accessed patterns

## Dependencies

Required Python packages:
```bash
pip install neo4j>=5.0.0
```

This installs the Python driver that works with both Neo4j and Memgraph.

## Additional Resources

- [Memgraph Documentation](https://memgraph.com/docs)
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)
