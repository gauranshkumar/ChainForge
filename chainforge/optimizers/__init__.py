"""Optimizer module for ChainForge."""
import sys
import os
from chainforge.optimizers.protocol import OptimizerRegistry

# Import optimizer implementations to register them
# This must happen so the @OptimizerRegistry.register decorators run
# Using relative import to avoid circular import issues
from . import evolutionary  # noqa: F401

# Debug: Write to file AND print to ensure visibility
registered = OptimizerRegistry.list_methods()
debug_msg = f"\n{'='*60}\nOPTIMIZERS MODULE LOADED\nRegistered methods: {registered}\n{'='*60}\n"

# Write to file
try:
    with open('/tmp/chainforge_optimizer_debug.log', 'w') as f:
        f.write(debug_msg)
        f.write(f"Module file: {__file__}\n")
        f.write(f"Working dir: {os.getcwd()}\n")
except:
    pass

# Also print
print(debug_msg, file=sys.stderr)
sys.stderr.flush()

__all__ = ["OptimizerRegistry"]
