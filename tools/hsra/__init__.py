"""HSRA - Historical State Reconstruction Adapter (minimal package)

This package implements a strict, fail-closed adapter that transforms
quote+trade CSV inputs into canonical JSONL ticker events when and only when
the requested window is complete according to the repository contract.
"""
__version__ = "0.1.0"
