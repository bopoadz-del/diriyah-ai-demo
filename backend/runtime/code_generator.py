"""Code generator using LLM for natural language to Python conversion."""

from __future__ import annotations

import ast
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Approved modules for code generation
APPROVED_MODULES: Set[str] = {
    "pandas",
    "numpy",
    "datetime",
    "statistics",
    "math",
    "json",
    "collections",
    "re",
    "itertools",
}

# Forbidden patterns that should never appear in generated code
FORBIDDEN_PATTERNS: List[str] = [
    "__import__",
    "eval",
    "exec",
    "compile",
    "open",
    "file",
    "input",
    "os.",
    "sys.",
    "subprocess.",
    "socket.",
    "shutil.",
    "pathlib.",
    "importlib.",
    "builtins.",
    "globals()",
    "locals()",
    "getattr",
    "setattr",
    "delattr",
]

SYSTEM_PROMPT = """
You are a Python code generator for construction analytics.
Generate safe, executable code to answer: {query}

Available context:
{context_description}

RULES:
1. Only import: pandas, numpy, datetime, statistics, math, json, collections, re, itertools
2. NEVER use: os, sys, subprocess, eval, exec, open, file, __import__, socket, shutil
3. Store final result in variable named 'result'
4. Add try/except error handling
5. Keep execution under 5 seconds
6. Add explanatory comments
7. Use the provided context variables directly (they're already defined)

Available context variables:
{context_variables}

Example:
```python
import pandas as pd

try:
    # Calculate steel cost variance
    steel_items = [item for item in boq_items if 'steel' in item.get('description', '').lower()]
    total = sum(item.get('quantity', 0) * item.get('unit_cost', 0) for item in steel_items)
    variance = total * 0.15
    result = {{'original': total, 'increased': total * 1.15, 'variance': variance, 'items_count': len(steel_items)}}
except Exception as e:
    result = {{'error': str(e)}}
```

IMPORTANT: Return ONLY the Python code, no explanations or markdown.
"""


class CodeGenerator:
    """Generates Python code from natural language queries using LLM."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        """Initialize the code generator.

        Args:
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
            model: OpenAI model to use for code generation.
        """
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._model = model
        self._openai = None

    def _get_openai(self):
        """Lazy-load OpenAI client."""
        if self._openai is None:
            try:
                import openai

                if self._api_key:
                    openai.api_key = self._api_key
                self._openai = openai
            except ImportError:
                logger.warning("OpenAI not installed; using template-based generation")
                self._openai = False
        return self._openai

    def generate_code(self, query: str, context: Dict[str, Any]) -> str:
        """Generate Python code from a natural language query.

        Args:
            query: Natural language description of the desired computation.
            context: Dictionary of available data and context.

        Returns:
            Generated Python code string.
        """
        context_description = self._build_context_description(context)
        context_variables = self._build_context_variables(context)

        prompt = SYSTEM_PROMPT.format(
            query=query,
            context_description=context_description,
            context_variables=context_variables,
        )

        openai = self._get_openai()
        if openai and openai is not False:
            try:
                response = openai.ChatCompletion.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": "You are a Python code generator."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                    max_tokens=1000,
                )
                code = response.choices[0].message.content.strip()
                # Remove markdown code blocks if present
                code = self._extract_code_from_markdown(code)
                return code
            except Exception as e:
                logger.error("OpenAI API error: %s", e)
                return self._generate_fallback_code(query, context)
        else:
            return self._generate_fallback_code(query, context)

    def _extract_code_from_markdown(self, text: str) -> str:
        """Extract Python code from markdown code blocks."""
        # Match ```python ... ``` or ``` ... ```
        pattern = r"```(?:python)?\s*([\s\S]*?)```"
        matches = re.findall(pattern, text)
        if matches:
            return matches[0].strip()
        return text

    def _build_context_description(self, context: Dict[str, Any]) -> str:
        """Build a description of available context."""
        descriptions = []
        for key, value in context.items():
            if isinstance(value, list):
                descriptions.append(f"- {key}: List of {len(value)} items")
                if value and isinstance(value[0], dict):
                    descriptions.append(f"  Keys: {list(value[0].keys())}")
            elif isinstance(value, dict):
                descriptions.append(f"- {key}: Dictionary with keys {list(value.keys())}")
            else:
                descriptions.append(f"- {key}: {type(value).__name__}")
        return "\n".join(descriptions) if descriptions else "No context provided"

    def _build_context_variables(self, context: Dict[str, Any]) -> str:
        """Build list of available context variables."""
        return ", ".join(context.keys()) if context else "None"

    def _generate_fallback_code(self, query: str, context: Dict[str, Any]) -> str:
        """Generate simple template-based code when LLM is unavailable."""
        query_lower = query.lower()

        # Detect common query patterns and generate appropriate code
        if "sum" in query_lower or "total" in query_lower:
            if "boq" in query_lower or "quantity" in query_lower:
                return self._template_boq_sum(context)
            return self._template_simple_sum()

        if "variance" in query_lower or "increase" in query_lower or "decrease" in query_lower:
            return self._template_variance(query_lower, context)

        if "monte carlo" in query_lower or "simulation" in query_lower:
            return self._template_monte_carlo(context)

        if "average" in query_lower or "mean" in query_lower:
            return self._template_average(context)

        # Default: return context summary
        return self._template_context_summary(context)

    def _template_boq_sum(self, context: Dict[str, Any]) -> str:
        """Template for BOQ sum calculations."""
        return """import json

try:
    boq_items = context.get('boq_items', [])
    total_quantity = sum(item.get('quantity', 0) for item in boq_items)
    total_cost = sum(
        item.get('quantity', 0) * item.get('unit_cost', 0)
        for item in boq_items
    )
    result = {
        'total_items': len(boq_items),
        'total_quantity': total_quantity,
        'total_cost': total_cost
    }
except Exception as e:
    result = {'error': str(e)}
"""

    def _template_simple_sum(self) -> str:
        """Template for simple sum calculations."""
        return """try:
    # Sum calculation
    values = context.get('values', [])
    result = {'sum': sum(values), 'count': len(values)}
except Exception as e:
    result = {'error': str(e)}
"""

    def _template_variance(self, query: str, context: Dict[str, Any]) -> str:
        """Template for variance calculations."""
        # Try to extract percentage from query
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", query)
        percentage = float(pct_match.group(1)) / 100 if pct_match else 0.15

        return f"""try:
    boq_items = context.get('boq_items', [])
    total_cost = sum(
        item.get('quantity', 0) * item.get('unit_cost', 0)
        for item in boq_items
    )
    percentage = {percentage}
    variance = total_cost * percentage
    result = {{
        'original_cost': total_cost,
        'percentage_change': percentage * 100,
        'variance': variance,
        'new_cost': total_cost * (1 + percentage)
    }}
except Exception as e:
    result = {{'error': str(e)}}
"""

    def _template_monte_carlo(self, context: Dict[str, Any]) -> str:
        """Template for Monte Carlo simulation."""
        return """import numpy as np
import statistics

try:
    values = context.get('values', context.get('boq_items', []))
    if isinstance(values, list) and values and isinstance(values[0], dict):
        values = [item.get('quantity', 0) * item.get('unit_cost', 0) for item in values]

    iterations = min(context.get('iterations', 1000), 10000)

    if not values:
        result = {'error': 'No values provided for simulation'}
    else:
        mean_val = statistics.mean(values) if values else 0
        std_val = statistics.stdev(values) if len(values) > 1 else 0

        simulations = np.random.normal(mean_val, std_val, iterations)

        result = {
            'mean': float(np.mean(simulations)),
            'std': float(np.std(simulations)),
            'percentile_10': float(np.percentile(simulations, 10)),
            'percentile_90': float(np.percentile(simulations, 90)),
            'iterations': iterations
        }
except Exception as e:
    result = {'error': str(e)}
"""

    def _template_average(self, context: Dict[str, Any]) -> str:
        """Template for average calculations."""
        return """import statistics

try:
    values = context.get('values', [])
    if not values:
        boq_items = context.get('boq_items', [])
        values = [item.get('quantity', 0) for item in boq_items]

    if values:
        result = {
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'count': len(values)
        }
    else:
        result = {'error': 'No values to calculate average'}
except Exception as e:
    result = {'error': str(e)}
"""

    def _template_context_summary(self, context: Dict[str, Any]) -> str:
        """Template that summarizes available context."""
        return """try:
    summary = {}
    for key, value in context.items():
        if isinstance(value, list):
            summary[key] = {'type': 'list', 'count': len(value)}
        elif isinstance(value, dict):
            summary[key] = {'type': 'dict', 'keys': list(value.keys())}
        else:
            summary[key] = {'type': type(value).__name__, 'value': str(value)[:100]}
    result = {'context_summary': summary}
except Exception as e:
    result = {'error': str(e)}
"""

    def validate_code(self, code: str) -> Dict[str, Any]:
        """Validate generated code for safety.

        Args:
            code: Python code to validate.

        Returns:
            Dictionary with validation results.
        """
        violations = []
        approved_imports = []
        forbidden_imports = []

        # Check for forbidden patterns
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in code:
                violations.append(f"Forbidden pattern: {pattern}")

        # Parse and check imports
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name.split(".")[0]
                        if module in APPROVED_MODULES:
                            approved_imports.append(module)
                        else:
                            forbidden_imports.append(module)
                            violations.append(f"Forbidden import: {module}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module = node.module.split(".")[0]
                        if module in APPROVED_MODULES:
                            approved_imports.append(module)
                        else:
                            forbidden_imports.append(module)
                            violations.append(f"Forbidden import: {module}")
        except SyntaxError as e:
            violations.append(f"Syntax error: {e}")

        return {
            "is_safe": len(violations) == 0,
            "violations": violations,
            "approved_imports": list(set(approved_imports)),
            "forbidden_imports": list(set(forbidden_imports)),
        }

    def extract_imports(self, code: str) -> List[str]:
        """Extract import statements from code.

        Args:
            code: Python code to analyze.

        Returns:
            List of imported module names.
        """
        imports = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except SyntaxError:
            # Fall back to regex for malformed code
            import_pattern = r"^(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)"
            imports = re.findall(import_pattern, code, re.MULTILINE)
        return imports
