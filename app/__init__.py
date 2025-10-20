"""Application package initializer.

Ensures the local ``app`` package takes precedence over similarly named
dependencies that might be installed in the environment.
"""

# The package intentionally re-exports nothing; the presence of this file is
# sufficient for Python to treat ``app`` as a regular package instead of
# falling back to namespace package resolution that could pick up unrelated
# modules from site-packages.

