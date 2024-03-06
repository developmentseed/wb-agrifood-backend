"""
For some reason, this file was necessary to make mypy happy.

Mypy was complaining that the same module (config.py) was being imported under
two different names (config and utils.config), which it was, because I needed
to import it in two different places. Would love to understand why that's a
problem for mypy.
"""
from __future__ import annotations
