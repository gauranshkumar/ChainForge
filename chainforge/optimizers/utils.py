"""Utility functions for optimizers."""
from typing import List, Dict, Any, Tuple, Optional
import re
import numpy as np
from sklearn.metrics import matthews_corrcoef, balanced_accuracy_score, confusion_matrix


def calculate_mcc(y_true: List, y_pred: List) -> float:
    """Calculate Matthews Correlation Coefficient (MCC)."""
    try:
        return matthews_corrcoef(y_true, y_pred)
    except Exception as e:
        print(f"Error calculating MCC: {e}")
        return 0.0


def calculate_balanced_accuracy(y_true: List, y_pred: List) -> float:
    """Calculate Balanced Accuracy Score."""
    try:
        return balanced_accuracy_score(y_true, y_pred)
    except Exception as e:
        print(f"Error calculating balanced accuracy: {e}")
        return 0.0


def calculate_fitness(
    y_true: List,
    y_pred: List,
    metric: str = "mcc"
) -> float:
    """
    Calculate fitness score based on specified metric.

    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        metric: Metric to use ('mcc' or 'balanced_accuracy')

    Returns:
        Fitness score
    """
    if metric == "mcc":
        return calculate_mcc(y_true, y_pred)
    elif metric == "balanced_accuracy":
        return calculate_balanced_accuracy(y_true, y_pred)
    elif metric == "custom":
        # For custom metric, y_pred contains the scores directly
        # We process them to ensure they are float numbers
        try:
            scores = [float(s) for s in y_pred if s is not None]
            if not scores:
                return 0.0
            return float(np.mean(scores))
        except (ValueError, TypeError):
            print(f"Error calculating custom fitness: predicted values are not numbers. First few: {y_pred[:5]}")
            return 0.0
    else:
        raise ValueError(f"Unknown metric: {metric}")


def tournament_selection(
    population: List[Dict[str, Any]],
    fitness_scores: List[float],
    tournament_size: int = 3
) -> Dict[str, Any]:
    """
    Select an individual using tournament selection.

    Args:
        population: List of individuals (prompts with metadata)
        fitness_scores: Corresponding fitness scores
        tournament_size: Number of individuals in tournament

    Returns:
        Selected individual
    """
    tournament_indices = np.random.choice(
        len(population),
        size=min(tournament_size, len(population)),
        replace=False
    )
    tournament_fitness = [fitness_scores[i] for i in tournament_indices]
    winner_idx = tournament_indices[np.argmax(tournament_fitness)]
    return population[winner_idx]


def roulette_wheel_selection(
    population: List[Dict[str, Any]],
    fitness_scores: List[float]
) -> Dict[str, Any]:
    """
    Select an individual using roulette wheel selection.

    Args:
        population: List of individuals (prompts with metadata)
        fitness_scores: Corresponding fitness scores

    Returns:
        Selected individual
    """
    # Shift fitness scores to be non-negative
    min_fitness = min(fitness_scores)
    if min_fitness < 0:
        adjusted_fitness = [f - min_fitness + 1e-6 for f in fitness_scores]
    else:
        adjusted_fitness = [f + 1e-6 for f in fitness_scores]  # Add small epsilon to avoid division by zero

    total_fitness = sum(adjusted_fitness)
    probabilities = [f / total_fitness for f in adjusted_fitness]

    selected_idx = np.random.choice(len(population), p=probabilities)
    return population[selected_idx]


def extract_data_sections(prompt: str) -> Tuple[List[Tuple[int, int]], List[str]]:
    """
    Extract protected data sections from a prompt.

    Data sections can be marked with:
    - [DATA]...[/DATA] tags
    - ```...``` code blocks
    - Lines starting with "Example:", "Input:", "Output:"

    Args:
        prompt: The prompt text

    Returns:
        Tuple of (protected_ranges, data_sections)
        - protected_ranges: List of (start, end) character indices
        - data_sections: List of the actual data section texts
    """
    protected_ranges = []
    data_sections = []

    # Match [DATA]...[/DATA] tags
    for match in re.finditer(r'\[DATA\](.*?)\[/DATA\]', prompt, re.DOTALL):
        protected_ranges.append((match.start(), match.end()))
        data_sections.append(match.group(0))

    # Match code blocks ```...```
    for match in re.finditer(r'```(.*?)```', prompt, re.DOTALL):
        protected_ranges.append((match.start(), match.end()))
        data_sections.append(match.group(0))

    # Match example blocks (lines starting with Example:, Input:, Output:)
    lines = prompt.split('\n')
    current_pos = 0
    in_example_block = False
    block_start = 0

    for line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith(('Example:', 'Input:', 'Output:', 'Q:', 'A:')):
            if not in_example_block:
                block_start = current_pos
                in_example_block = True
        elif in_example_block and line_stripped == '':
            # End of example block
            protected_ranges.append((block_start, current_pos))
            data_sections.append(prompt[block_start:current_pos])
            in_example_block = False

        current_pos += len(line) + 1  # +1 for newline

    # If still in example block at end
    if in_example_block:
        protected_ranges.append((block_start, len(prompt)))
        data_sections.append(prompt[block_start:len(prompt)])

    return protected_ranges, data_sections


def split_preserving_data(prompt: str) -> Tuple[List[str], List[bool]]:
    """
    Split prompt into segments, marking which are data sections.

    Args:
        prompt: The prompt text

    Returns:
        Tuple of (segments, is_data_flags)
        - segments: List of text segments
        - is_data_flags: List of booleans indicating if segment is data
    """
    protected_ranges, _ = extract_data_sections(prompt)

    if not protected_ranges:
        # No data sections, treat entire prompt as mutable
        return [prompt], [False]

    # Sort ranges
    protected_ranges.sort(key=lambda x: x[0])

    segments = []
    is_data_flags = []
    current_pos = 0

    for start, end in protected_ranges:
        # Add mutable text before data section
        if start > current_pos:
            segments.append(prompt[current_pos:start])
            is_data_flags.append(False)

        # Add data section
        segments.append(prompt[start:end])
        is_data_flags.append(True)
        current_pos = end

    # Add remaining mutable text
    if current_pos < len(prompt):
        segments.append(prompt[current_pos:])
        is_data_flags.append(False)

    return segments, is_data_flags


def parse_predictions(results: List[Dict[str, Any]]) -> Tuple[List, List]:
    """
    Parse evaluation results to extract true and predicted labels.

    Args:
        results: List of evaluation results from ChainForge

    Returns:
        Tuple of (y_true, y_pred)
    """
    y_true = []
    y_pred = []

    for result in results:
        if "eval_res" in result and result["eval_res"]:
            eval_data = result["eval_res"]

            # Handle different evaluation result formats
            if isinstance(eval_data, dict):
                if "true_label" in eval_data and "predicted_label" in eval_data:
                    y_true.append(eval_data["true_label"])
                    y_pred.append(eval_data["predicted_label"])
                elif "items" in eval_data and len(eval_data["items"]) > 0:
                    # Extract from items array
                    for item in eval_data["items"]:
                        if isinstance(item, dict):
                            if "true" in item and "pred" in item:
                                y_true.append(item["true"])
                                y_pred.append(item["pred"])

    return y_true, y_pred
