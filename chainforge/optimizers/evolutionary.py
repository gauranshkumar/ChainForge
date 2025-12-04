"""Evolutionary Algorithm optimizer for prompt engineering."""
from typing import List, Dict, Any, Optional, Tuple, Callable
import numpy as np
import random
import asyncio
import inspect
from chainforge.optimizers.protocol import OptimizerRegistry
from chainforge.optimizers.utils import (
    calculate_fitness,
    tournament_selection,
    roulette_wheel_selection,
    parse_predictions,
    split_preserving_data
)


class Individual:
    """Represents an individual in the population (a prompt)."""

    def __init__(self, prompt: str, metadata: Optional[Dict[str, Any]] = None):
        self.prompt = prompt
        self.metadata = metadata or {}
        self.fitness = None
        self.evaluation_results = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert individual to dictionary format."""
        return {
            "prompt": self.prompt,
            "fitness": self.fitness,
            "metadata": self.metadata,
            "evaluation_results": self.evaluation_results
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Individual':
        """Create individual from dictionary format."""
        ind = cls(data["prompt"], data.get("metadata", {}))
        ind.fitness = data.get("fitness")
        ind.evaluation_results = data.get("evaluation_results")
        return ind


def reconstruct_with_data(
    mutable_text: str,
    original_segments: List[str],
    is_data_flags: List[bool]
) -> str:
    """
    Reconstruct a prompt by combining mutated text with original data sections.

    Args:
        mutable_text: The modified instruction text
        original_segments: Original segments from parent
        is_data_flags: Flags indicating which segments are data

    Returns:
        Reconstructed prompt with data sections preserved
    """
    result_parts = []
    mutable_used = False

    for segment, is_data in zip(original_segments, is_data_flags):
        if is_data:
            # Keep data section unchanged
            result_parts.append(segment)
        else:
            # Replace with mutated text (only first mutable section)
            if not mutable_used:
                result_parts.append(mutable_text)
                mutable_used = True

    return "".join(result_parts)


def semantic_crossover(
    parent1: str,
    parent2: str,
    nlp_model: Optional[Any] = None
) -> Tuple[str, str]:
    """
    Perform semantic chunking-based crossover while preserving data sections.

    Uses spaCy to identify semantic chunks (sentences) and swaps them
    between parents. Data sections marked with [DATA]...[/DATA], code blocks,
    or example lines are preserved.

    Args:
        parent1: First parent prompt
        parent2: Second parent prompt
        nlp_model: spaCy NLP model (optional, loaded if not provided)

    Returns:
        Tuple of two offspring prompts
    """
    # Split prompts into mutable and data sections
    segments1, is_data1 = split_preserving_data(parent1)
    segments2, is_data2 = split_preserving_data(parent2)

    # Extract only mutable (non-data) segments for crossover
    mutable1 = [seg for seg, is_data in zip(segments1, is_data1) if not is_data]
    mutable2 = [seg for seg, is_data in zip(segments2, is_data2) if not is_data]

    # If no mutable sections, return parents unchanged
    if not mutable1 or not mutable2:
        return parent1, parent2

    # Perform crossover on mutable text only
    mutable_text1 = " ".join(mutable1)
    mutable_text2 = " ".join(mutable2)

    try:
        import spacy

        if nlp_model is None:
            try:
                nlp_model = spacy.load("en_core_web_sm")
            except OSError:
                return simple_sentence_crossover(mutable_text1, mutable_text2, parent1, parent2, segments1, is_data1, segments2, is_data2)

        # Parse mutable text into sentences
        doc1 = nlp_model(mutable_text1)
        doc2 = nlp_model(mutable_text2)

        sents1 = [sent.text.strip() for sent in doc1.sents]
        sents2 = [sent.text.strip() for sent in doc2.sents]

        if len(sents1) == 0 or len(sents2) == 0:
            return simple_sentence_crossover(mutable_text1, mutable_text2, parent1, parent2, segments1, is_data1, segments2, is_data2)

        # Crossover on sentences
        crossover_point1 = random.randint(0, len(sents1))
        crossover_point2 = random.randint(0, len(sents2))

        offspring1_mutable = " ".join(sents1[:crossover_point1] + sents2[crossover_point2:])
        offspring2_mutable = " ".join(sents2[:crossover_point2] + sents1[crossover_point1:])

        # Reconstruct offspring by combining mutable text with original data sections
        offspring1 = reconstruct_with_data(offspring1_mutable, segments1, is_data1)
        offspring2 = reconstruct_with_data(offspring2_mutable, segments2, is_data2)

        return offspring1, offspring2

    except ImportError:
        return simple_sentence_crossover(mutable_text1, mutable_text2, parent1, parent2, segments1, is_data1, segments2, is_data2)


def simple_sentence_crossover(
    mutable1: str,
    mutable2: str,
    parent1: str,
    parent2: str,
    segments1: List[str],
    is_data1: List[bool],
    segments2: List[str],
    is_data2: List[bool]
) -> Tuple[str, str]:
    """
    Simple sentence-based crossover without NLP, preserving data sections.

    Args:
        mutable1: Mutable text from parent1
        mutable2: Mutable text from parent2
        parent1: Full parent1 prompt
        parent2: Full parent2 prompt
        segments1: Segments from parent1
        is_data1: Data flags from parent1
        segments2: Segments from parent2
        is_data2: Data flags from parent2

    Returns:
        Tuple of two offspring prompts
    """
    # Split on periods (simple sentence splitting)
    sents1 = [s.strip() + "." for s in mutable1.split(".") if s.strip()]
    sents2 = [s.strip() + "." for s in mutable2.split(".") if s.strip()]

    if len(sents1) == 0:
        sents1 = [mutable1]
    if len(sents2) == 0:
        sents2 = [mutable2]

    crossover_point1 = random.randint(0, len(sents1))
    crossover_point2 = random.randint(0, len(sents2))

    offspring1_mutable = " ".join(sents1[:crossover_point1] + sents2[crossover_point2:])
    offspring2_mutable = " ".join(sents2[:crossover_point2] + sents1[crossover_point1:])

    # Reconstruct with data
    offspring1 = reconstruct_with_data(offspring1_mutable, segments1, is_data1)
    offspring2 = reconstruct_with_data(offspring2_mutable, segments2, is_data2)

    return offspring1, offspring2


def neo4j_mutation(
    prompt: str,
    neo4j_connection: Optional[Dict[str, Any]] = None,
    mutation_rate: float = 0.3
) -> str:
    """
    Perform mutation using Memgraph/Neo4j prompt taxonomy while preserving data sections.

    Connects to Memgraph database containing Pattern nodes with template labels,
    organized by Category and SubCategory. Fetches templates from different
    categories to ensure diversity in mutation.

    Data sections marked with [DATA]...[/DATA], code blocks, or example lines
    are preserved unchanged.

    Expected graph structure:
    - (Pattern {label: "template text"})-[:BELONGS_TO]->(SubCategory)
    - (SubCategory)-[:BELONGS_TO]->(Category)
    - Or: (Pattern)-[:BELONGS_TO]->(Category)

    Args:
        prompt: The prompt to mutate
        neo4j_connection: Dict with 'uri', 'user', 'password' for Memgraph connection
                         Default uri: bolt://localhost:7688
        mutation_rate: Probability of mutation

    Returns:
        Mutated prompt with data sections preserved
    """
    if random.random() > mutation_rate:
        return prompt

    # Split into mutable and data sections
    segments, is_data_flags = split_preserving_data(prompt)

    # Extract mutable text
    mutable_segments = [seg for seg, is_data in zip(segments, is_data_flags) if not is_data]

    if not mutable_segments:
        # No mutable sections, return unchanged
        return prompt

    mutable_text = " ".join(mutable_segments)

    if neo4j_connection is None:
        # Fallback to simple word-level mutation
        mutated_text = simple_word_mutation(mutable_text, mutation_rate)
        return reconstruct_with_data(mutated_text, segments, is_data_flags)

    try:
        from neo4j import GraphDatabase

        uri = neo4j_connection.get("uri", "bolt://localhost:7688")
        user = neo4j_connection.get("user", "")
        password = neo4j_connection.get("password", "")

        # Memgraph typically doesn't require auth, but support it if provided
        if user and password:
            driver = GraphDatabase.driver(uri, auth=(user, password))
        else:
            driver = GraphDatabase.driver(uri, auth=None)

        with driver.session() as session:
            # Step 1: Try to identify the current prompt's category/subcategory
            # This helps us fetch templates from DIFFERENT categories
            current_category = None
            current_subcategory = None

            try:
                # Try to find if the mutable text matches any existing pattern
                category_result = session.run(
                    """
                    MATCH (p:Pattern)
                    WHERE p.label CONTAINS $search_term
                    OPTIONAL MATCH (p)-[:BELONGS_TO]->(sc:SubCategory)
                    OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
                    OPTIONAL MATCH (sc)-[:BELONGS_TO]->(c2:Category)
                    RETURN sc.name as subcategory,
                           COALESCE(c.name, c2.name) as category
                    LIMIT 1
                    """,
                    search_term=mutable_text[:50]
                )

                record = category_result.single()
                if record:
                    current_subcategory = record.get("subcategory")
                    current_category = record.get("category")
            except Exception as e:
                print(f"Could not determine current category: {e}")

            # Step 2: Fetch templates from DIFFERENT categories/subcategories
            # This ensures diversity in mutation
            templates = []

            # Query 1: Try to get patterns from different subcategories
            if current_subcategory:
                result = session.run(
                    """
                    MATCH (p:Pattern)-[:BELONGS_TO]->(sc:SubCategory)
                    WHERE sc.name <> $current_subcategory AND p.label IS NOT NULL
                    RETURN DISTINCT p.label as template
                    LIMIT 10
                    """,
                    current_subcategory=current_subcategory
                )
                templates = [record["template"] for record in result if record["template"]]

            # Query 2: If no results or no subcategory, try different categories
            if not templates and current_category:
                result = session.run(
                    """
                    MATCH (p:Pattern)-[:BELONGS_TO*1..2]->(c:Category)
                    WHERE c.name <> $current_category AND p.label IS NOT NULL
                    RETURN DISTINCT p.label as template
                    LIMIT 10
                    """,
                    current_category=current_category
                )
                templates = [record["template"] for record in result if record["template"]]

            # Query 3: Fallback - just get any patterns if nothing else works
            if not templates:
                result = session.run(
                    """
                    MATCH (p:Pattern)
                    WHERE p.label IS NOT NULL
                    RETURN p.label as template
                    LIMIT 10
                    """
                )
                templates = [record["template"] for record in result if record["template"]]

            # Step 3: Select a random template and perform mutation on mutable text
            if templates:
                # Select a random template
                selected_template = random.choice(templates)

                # Perform template-based mutation on mutable text only
                # Split mutable text into sentences and replace one with template
                try:
                    import spacy
                    nlp = spacy.load("en_core_web_sm")
                    doc = nlp(mutable_text)
                    sents = [sent.text.strip() for sent in doc.sents]
                except (ImportError, OSError):
                    sents = [s.strip() + "." for s in mutable_text.split(".") if s.strip()]

                if len(sents) > 0:
                    # Replace a random sentence
                    replace_idx = random.randint(0, len(sents) - 1)
                    sents[replace_idx] = selected_template
                    mutated_text = " ".join(sents)

                    # Reconstruct with data sections
                    return reconstruct_with_data(mutated_text, segments, is_data_flags)

        driver.close()

    except ImportError:
        print("neo4j package not installed, using simple mutation")
        mutated_text = simple_word_mutation(mutable_text, mutation_rate)
        return reconstruct_with_data(mutated_text, segments, is_data_flags)
    except Exception as e:
        print(f"Error during Memgraph mutation: {e}")
        import traceback
        traceback.print_exc()
        mutated_text = simple_word_mutation(mutable_text, mutation_rate)
        return reconstruct_with_data(mutated_text, segments, is_data_flags)

    return prompt


def simple_word_mutation(prompt: str, mutation_rate: float = 0.3) -> str:
    """
    Simple word-level mutation (fallback).

    Randomly swaps or removes words.

    Args:
        prompt: The prompt to mutate
        mutation_rate: Probability of mutating each word

    Returns:
        Mutated prompt
    """
    words = prompt.split()

    if len(words) < 2:
        return prompt

    for i in range(len(words)):
        if random.random() < mutation_rate / len(words):
            # Swap with adjacent word
            if i < len(words) - 1:
                words[i], words[i + 1] = words[i + 1], words[i]

    return " ".join(words)


@OptimizerRegistry.register("evolutionary_algorithm")
async def evolutionary_algorithm_optimizer(
    initial_prompts: List[str],
    evaluation_function: Callable,
    settings: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evolutionary Algorithm optimizer for prompt engineering.

    Args:
        initial_prompts: List of initial prompt strings
        evaluation_function: Function (sync or async) that takes a prompt and returns evaluation results
        settings: Configuration dict with:
            - population_size: int (default: 10)
            - num_generations: int (default: 5)
            - mutation_rate: float (default: 0.3)
            - crossover_rate: float (default: 0.7)
            - selection_method: str ('tournament' or 'roulette', default: 'tournament')
            - tournament_size: int (default: 3)
            - fitness_metric: str ('mcc' or 'balanced_accuracy', default: 'mcc')
            - elitism_count: int (default: 2)
            - neo4j_uri: str (optional)
            - neo4j_user: str (optional)
            - neo4j_password: str (optional)

    Returns:
        Dict containing optimization results
    """
    # Extract settings with defaults
    population_size = int(settings.get("population_size", 10))
    num_generations = int(settings.get("num_generations", 5))
    mutation_rate = float(settings.get("mutation_rate", 0.3))
    crossover_rate = float(settings.get("crossover_rate", 0.7))
    selection_method = settings.get("selection_method", "tournament")
    tournament_size = int(settings.get("tournament_size", 3))
    fitness_metric = settings.get("fitness_metric", "mcc")
    elitism_count = int(settings.get("elitism_count", 2))

    # Neo4j connection (optional)
    neo4j_connection = None
    if all(k in settings for k in ["neo4j_uri", "neo4j_user", "neo4j_password"]):
        neo4j_connection = {
            "uri": settings["neo4j_uri"],
            "user": settings["neo4j_user"],
            "password": settings["neo4j_password"]
        }

    # Load spaCy model once for all crossover operations
    nlp_model = None
    try:
        import spacy
        nlp_model = spacy.load("en_core_web_sm")
    except (ImportError, OSError):
        print("spaCy not available, using simple crossover")

    # Initialize population
    population = [Individual(prompt) for prompt in initial_prompts]

    # Pad population if needed
    while len(population) < population_size:
        # Duplicate and mutate existing prompts
        base_prompt = random.choice(initial_prompts)
        mutated = neo4j_mutation(base_prompt, neo4j_connection, mutation_rate)
        population.append(Individual(mutated))

    # Track best individuals across generations
    history = []
    best_individual = None
    best_fitness = float('-inf')

    # Check if evaluation_function is async
    is_async_eval = asyncio.iscoroutinefunction(evaluation_function)

    # Main evolutionary loop
    for generation in range(num_generations):
        print(f"Generation {generation + 1}/{num_generations}")

        # Evaluate population
        for individual in population:
            # Get evaluation results from the evaluation function
            if is_async_eval:
                eval_results = await evaluation_function(individual.prompt)
            else:
                eval_results = evaluation_function(individual.prompt)
            individual.evaluation_results = eval_results

            # Parse predictions and calculate fitness
            y_true, y_pred = parse_predictions(eval_results)

            if len(y_true) > 0 and len(y_pred) > 0:
                individual.fitness = calculate_fitness(y_true, y_pred, fitness_metric)
            else:
                # No valid predictions, assign worst fitness
                individual.fitness = float('-inf')

        # Track best individual
        fitness_scores = [ind.fitness for ind in population]
        gen_best_idx = np.argmax(fitness_scores)
        gen_best = population[gen_best_idx]

        if gen_best.fitness > best_fitness:
            best_fitness = gen_best.fitness
            best_individual = gen_best

        # Record generation stats
        history.append({
            "generation": generation + 1,
            "best_fitness": float(gen_best.fitness),
            "avg_fitness": float(np.mean(fitness_scores)),
            "best_prompt": gen_best.prompt
        })

        print(f"  Best fitness: {gen_best.fitness:.4f}")
        print(f"  Avg fitness: {np.mean(fitness_scores):.4f}")

        # Create next generation
        if generation < num_generations - 1:
            new_population = []

            # Elitism: Keep best individuals
            sorted_pop = sorted(
                population,
                key=lambda ind: ind.fitness,
                reverse=True
            )
            new_population.extend(sorted_pop[:elitism_count])

            # Generate offspring
            while len(new_population) < population_size:
                # Selection
                if selection_method == "tournament":
                    parent1 = tournament_selection(population, fitness_scores, tournament_size)
                    parent2 = tournament_selection(population, fitness_scores, tournament_size)
                else:  # roulette
                    parent1 = roulette_wheel_selection(population, fitness_scores)
                    parent2 = roulette_wheel_selection(population, fitness_scores)

                # Crossover
                if random.random() < crossover_rate:
                    offspring1_text, offspring2_text = semantic_crossover(
                        parent1.prompt if isinstance(parent1, Individual) else parent1["prompt"],
                        parent2.prompt if isinstance(parent2, Individual) else parent2["prompt"],
                        nlp_model
                    )
                else:
                    # No crossover, just copy parents
                    offspring1_text = parent1.prompt if isinstance(parent1, Individual) else parent1["prompt"]
                    offspring2_text = parent2.prompt if isinstance(parent2, Individual) else parent2["prompt"]

                # Mutation
                offspring1_text = neo4j_mutation(offspring1_text, neo4j_connection, mutation_rate)
                offspring2_text = neo4j_mutation(offspring2_text, neo4j_connection, mutation_rate)

                # Add to new population
                new_population.append(Individual(offspring1_text))
                if len(new_population) < population_size:
                    new_population.append(Individual(offspring2_text))

            population = new_population

    # Return results
    return {
        "best_prompt": best_individual.prompt,
        "best_fitness": float(best_fitness),
        "history": history,
        "final_population": [ind.to_dict() for ind in population]
    }


def run_generation_step(
    generation: int,
    population: List[Dict[str, Any]],
    settings: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Run a single generation step of the evolutionary algorithm.

    This function is called by the frontend which handles LLM evaluation.
    The frontend provides the current population with fitness scores,
    and this function returns the next generation of prompts to evaluate.

    Args:
        generation: Current generation number (0 = initial population)
        population: List of {"prompt": str, "fitness": float} dicts
        settings: Optimizer configuration

    Returns:
        Dict containing:
        - new_population: List of prompt strings to evaluate
        - generation: Next generation number
        - best_fitness: Best fitness in current population
        - avg_fitness: Average fitness in current population
        - best_prompt: Best prompt so far
        - complete: True if this is the final generation
    """
    import random

    # Extract settings
    population_size = int(settings.get("population_size", 10))
    num_generations = int(settings.get("num_generations", 5))
    mutation_rate = float(settings.get("mutation_rate", 0.3))
    crossover_rate = float(settings.get("crossover_rate", 0.7))
    selection_method = settings.get("selection_method", "tournament")
    tournament_size = int(settings.get("tournament_size", 3))
    elitism_count = int(settings.get("elitism_count", 2))

    # Neo4j connection (optional)
    neo4j_connection = None
    if all(k in settings for k in ["neo4j_uri", "neo4j_user", "neo4j_password"]):
        neo4j_connection = {
            "uri": settings["neo4j_uri"],
            "user": settings["neo4j_user"],
            "password": settings["neo4j_password"]
        }

    # Load spaCy model for crossover
    nlp_model = None
    try:
        import spacy
        nlp_model = spacy.load("en_core_web_sm")
    except (ImportError, OSError):
        pass

    # Convert population to Individual objects with fitness
    individuals = []
    for item in population:
        ind = Individual(prompt=item["prompt"], metadata=item.get("metadata", {}))
        ind.fitness = item.get("fitness")
        individuals.append(ind)

    # Calculate statistics
    fitnesses = [ind.fitness for ind in individuals if ind.fitness is not None]
    best_fitness = max(fitnesses) if fitnesses else 0.0
    avg_fitness = sum(fitnesses) / len(fitnesses) if fitnesses else 0.0
    best_individual = max(individuals, key=lambda x: x.fitness if x.fitness is not None else float('-inf'))

    # Check if we're done
    if generation >= num_generations:
        return {
            "new_population": [],
            "generation": generation,
            "best_fitness": best_fitness,
            "avg_fitness": avg_fitness,
            "best_prompt": best_individual.prompt,
            "complete": True
        }

    # Sort population by fitness (descending)
    individuals.sort(key=lambda x: x.fitness if x.fitness is not None else float('-inf'), reverse=True)

    # Apply elitism - keep top individuals
    new_prompts = []
    elite_individuals = individuals[:elitism_count]
    new_prompts.extend([ind.prompt for ind in elite_individuals])

    # Prepare for selection (need dict format and fitness list for utils functions)
    pop_dicts = [ind.to_dict() for ind in individuals]
    fitness_list = [ind.fitness if ind.fitness is not None else float('-inf') for ind in individuals]

    # Generate rest of population through selection, crossover, mutation
    while len(new_prompts) < population_size:
        # Selection
        if selection_method == "tournament":
            parent1_dict = tournament_selection(pop_dicts, fitness_list, tournament_size)
            parent2_dict = tournament_selection(pop_dicts, fitness_list, tournament_size)
        else:  # roulette
            parent1_dict = roulette_wheel_selection(pop_dicts, fitness_list)
            parent2_dict = roulette_wheel_selection(pop_dicts, fitness_list)

        parent1_prompt = parent1_dict["prompt"]
        parent2_prompt = parent2_dict["prompt"]

        # Crossover
        if random.random() < crossover_rate:
            if nlp_model:
                # semantic_crossover returns tuple (child1, child2)
                child1, child2 = semantic_crossover(parent1_prompt, parent2_prompt, nlp_model)
                child_prompt = child1  # Use first offspring
            else:
                # Simple sentence-based crossover
                sentences1 = parent1_prompt.split('.')
                sentences2 = parent2_prompt.split('.')
                if len(sentences1) > 1 and len(sentences2) > 1:
                    crossover_point = random.randint(1, min(len(sentences1), len(sentences2)) - 1)
                    child_prompt = '.'.join(sentences1[:crossover_point] + sentences2[crossover_point:])
                else:
                    child_prompt = parent1_prompt
        else:
            child_prompt = parent1_prompt

        # Mutation
        if random.random() < mutation_rate:
            child_prompt = neo4j_mutation(child_prompt, neo4j_connection, mutation_rate)

        new_prompts.append(child_prompt)

    return {
        "new_population": new_prompts,
        "generation": generation + 1,
        "best_fitness": best_fitness,
        "avg_fitness": avg_fitness,
        "best_prompt": best_individual.prompt,
        "complete": False
    }
