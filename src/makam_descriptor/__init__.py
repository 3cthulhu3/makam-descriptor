"""Makam Descriptor — a culture-aware description tool for Turkish makam music."""
from .consistency import Params
from .theory import load_theory
from .tool import TOOL_SPEC, call_tool, describe, describe_notes

__version__ = "0.2.0"
__all__ = ["describe", "describe_notes", "call_tool", "load_theory", "Params", "TOOL_SPEC"]
