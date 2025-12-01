"""Registry and protocol for optimizer methods."""
import sys
from typing import Dict, Callable, Any, List


class OptimizerRegistry:
    """Registry for optimizer methods."""
    _methods: Dict[str, Callable] = {}

    @classmethod
    def register(cls, identifier: str):
        """Decorator to register an optimizer function."""
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("Method identifier must be a non-empty string.")

        def decorator(handler_func: Callable):
            if not callable(handler_func):
                raise TypeError("Registered handler must be a callable function.")
            if identifier in cls._methods:
                print(
                    f"Warning: Overwriting existing optimizer method '{identifier}'.",
                    file=sys.stderr,
                )
            cls._methods[identifier] = handler_func
            return handler_func

        return decorator

    @classmethod
    def get_handler(cls, identifier: str) -> Callable:
        """Get the handler function for a given method identifier."""
        handler = cls._methods.get(identifier)
        if handler is None:
            raise ValueError(f"Optimizer method '{identifier}' not found in registry.")
        return handler

    @classmethod
    def list_methods(cls) -> List[str]:
        """List all registered optimizer methods."""
        return list(cls._methods.keys())
