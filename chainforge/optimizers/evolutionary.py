"""Evolutionary Algorithm optimizer for prompt engineering."""
from typing import List, Dict, Any, Optional, Tuple, Callable
import numpy as np
import random
from chainforge.optimizers.protocol import OptimizerRegistry
from chainforge.optimizers.utils import (
    calculate_fitness,
    tournament_selection,
    roulette_wheel_selection,
    parse_predictions
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


def semantic_crossover(
    parent1: str,
    parent2: str,
    nlp_model: Optional[Any] = None
) -> Tuple[str, str]:
    """
    Perform semantic chunking-based crossover.

    Uses spaCy to identify semantic chunks (sentences) and swaps them
    between parents to create offspring.

    Args:
        parent1: First parent prompt
        parent2: Second parent prompt
        nlp_model: spaCy NLP model (optional, loaded if not provided)

    Returns:
        Tuple of two offspring prompts
    """
    try:
        import spacy

        if nlp_model is None:
            # Try to load a spacy model, fallback to simple sentence splitting
            try:
                nlp_model = spacy.load("en_core_web_sm")
            except OSError:
                # Fallback to simple sentence splitting
                return simple_sentence_crossover(parent1, parent2)

        # Parse both parents into semantic chunks (sentences)
        doc1 = nlp_model(parent1)
        doc2 = nlp_model(parent2)

        sents1 = [sent.text.strip() for sent in doc1.sents]
        sents2 = [sent.text.strip() for sent in doc2.sents]

        # If either parent has no sentences, fallback
        if len(sents1) == 0 or len(sents2) == 0:
            return simple_sentence_crossover(parent1, parent2)

        # Single-point crossover on sentences
        crossover_point1 = random.randint(0, len(sents1))
        crossover_point2 = random.randint(0, len(sents2))

        offspring1_sents = sents1[:crossover_point1] + sents2[crossover_point2:]
        offspring2_sents = sents2[:crossover_point2] + sents1[crossover_point1:]

        offspring1 = " ".join(offspring1_sents)
        offspring2 = " ".join(offspring2_sents)

        return offspring1, offspring2

    except ImportError:
        # If spacy is not available, use simple crossover
        return simple_sentence_crossover(parent1, parent2)


def simple_sentence_crossover(parent1: str, parent2: str) -> Tuple[str, str]:
    """
    Simple sentence-based crossover without NLP.

    Splits on periods and performs crossover.

    Args:
        parent1: First parent prompt
        parent2: Second parent prompt

    Returns:
        Tuple of two offspring prompts
    """
    # Split on periods (simple sentence splitting)
    sents1 = [s.strip() + "." for s in parent1.split(".") if s.strip()]
    sents2 = [s.strip() + "." for s in parent2.split(".") if s.strip()]

    if len(sents1) == 0:
        sents1 = [parent1]
    if len(sents2) == 0:
        sents2 = [parent2]

    crossover_point1 = random.randint(0, len(sents1))
    crossover_point2 = random.randint(0, len(sents2))

    offspring1_sents = sents1[:crossover_point1] + sents2[crossover_point2:]
    offspring2_sents = sents2[:crossover_point2] + sents1[crossover_point1:]

    offspring1 = " ".join(offspring1_sents)
    offspring2 = " ".join(offspring2_sents)

    return offspring1, offspring2


def neo4j_mutation(
    prompt: str,
    neo4j_connection: Optional[Dict[str, Any]] = None,
    mutation_rate: float = 0.3
) -> str:
    """
    Perform mutation using Neo4j prompt taxonomy.

    Connects to Neo4j database containing prompt templates and categories,
    and replaces parts of the prompt with semantically similar alternatives.

    Args:
        prompt: The prompt to mutate
        neo4j_connection: Dict with 'uri', 'user', 'password' for Neo4j connection
        mutation_rate: Probability of mutation

    Returns:
        Mutated prompt
    """
    if random.random() > mutation_rate:
        return prompt

    if neo4j_connection is None:
        # Fallback to simple word-level mutation
        return simple_word_mutation(prompt, mutation_rate)

    try:
        from neo4j import GraphDatabase

        uri = neo4j_connection.get("uri")
        user = neo4j_connection.get("user")
        password = neo4j_connection.get("password")

        if not all([uri, user, password]):
            return simple_word_mutation(prompt, mutation_rate)

        driver = GraphDatabase.driver(uri, auth=(user, password))

        with driver.session() as session:
            # Query to find similar prompt templates in the taxonomy
            # This assumes a graph structure like:
            # (PromptTemplate)-[:BELONGS_TO]->(Category)
            # (PromptTemplate)-[:SIMILAR_TO]->(PromptTemplate)
            result = session.run(
                """
                MATCH (p:PromptTemplate)
                WHERE p.text CONTAINS $search_term
                WITH p
                MATCH (p)-[:SIMILAR_TO*1..2]-(similar:PromptTemplate)
                RETURN DISTINCT similar.text as template
                LIMIT 5
                """,
                search_term=prompt[:50]  # Use first 50 chars as search term
            )

            templates = [record["template"] for record in result]

            if templates:
                # Select a random template
                selected_template = random.choice(templates)

                # Perform template-based mutation
                # Split prompt into sentences and replace one with template
                try:
                    import spacy
                    nlp = spacy.load("en_core_web_sm")
                    doc = nlp(prompt)
                    sents = [sent.text.strip() for sent in doc.sents]
                except (ImportError, OSError):
                    sents = [s.strip() + "." for s in prompt.split(".") if s.strip()]

                if len(sents) > 0:
                    # Replace a random sentence
                    replace_idx = random.randint(0, len(sents) - 1)
                    sents[replace_idx] = selected_template
                    return " ".join(sents)

        driver.close()

    except ImportError:
        print("neo4j package not installed, using simple mutation")
        return simple_word_mutation(prompt, mutation_rate)
    except Exception as e:
        print(f"Error during Neo4j mutation: {e}")
        return simple_word_mutation(prompt, mutation_rate)

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
def evolutionary_algorithm_optimizer(
    initial_prompts: List[str],
    evaluation_function: Callable,
    settings: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evolutionary Algorithm optimizer for prompt engineering.

    Args:
        initial_prompts: List of initial prompt strings
        evaluation_function: Function that takes a prompt and returns evaluation results
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

    # Main evolutionary loop
    for generation in range(num_generations):
        print(f"Generation {generation + 1}/{num_generations}")

        # Evaluate population
        for individual in population:
            # Get evaluation results from the evaluation function
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
