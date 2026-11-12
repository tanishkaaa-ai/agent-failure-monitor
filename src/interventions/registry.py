"""
Tool Registry for the Intervention Layer.
Maintains known tools and verified alternative/fallback tools.
Strict rule: Does NOT assume an alternative tool exists unless explicitly registered.
"""

from typing import Dict, List, Optional


class ToolRegistry:
    """Registry of available tools and verified fallback mappings."""

    def __init__(self):
        self._tools: Dict[str, Dict[str, Optional[str]]] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register default tools common in multi-agent benchmarks."""
        self.register(
            name="compute",
            fallback="python_interpreter",
            description="Symbolic/numeric math computation."
        )
        self.register(
            name="python_interpreter",
            fallback="bash_executor",
            description="Executes Python code snippet."
        )
        self.register(
            name="google_search",
            fallback="duckduckgo_search",
            description="Web search engine."
        )
        self.register(
            name="run_tests",
            fallback=None,  # No automated alternative for unit test runner
            description="Executes unit test suite."
        )
        self.register(
            name="record_lookup",
            fallback="sql_query",
            description="Database record search."
        )

    def register(
        self,
        name: str,
        fallback: Optional[str] = None,
        description: str = "",
    ) -> None:
        """Register a tool and its optional fallback alternative."""
        clean_name = name.strip()
        self._tools[clean_name] = {
            "fallback": fallback.strip() if fallback else None,
            "description": description,
        }

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name.strip() in self._tools

    def get_fallback(self, name: str) -> Optional[str]:
        """
        Get the registered fallback tool for a failing tool.
        Returns None if tool is unknown or has no registered fallback.
        """
        clean_name = name.strip()
        entry = self._tools.get(clean_name)
        if not entry:
            return None
        return entry.get("fallback")

    def list_tools(self) -> List[str]:
        """List all registered tools."""
        return list(self._tools.keys())

