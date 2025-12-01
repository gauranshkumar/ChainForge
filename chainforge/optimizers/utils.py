"""Utility functions for optimizers."""
from typing import List, Dict, Any, Tuple
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
