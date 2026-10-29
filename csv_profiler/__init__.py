"""Quick profiles of CSV datasets."""
from .core import read_table, infer_type, profile_column, profile, to_markdown

__version__ = "0.1.0"
__all__ = ["read_table", "infer_type", "profile_column", "profile", "to_markdown"]
