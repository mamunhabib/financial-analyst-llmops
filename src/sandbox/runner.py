"""
=============================================================================
FILE ROLE & CALL CHAIN CONTEXT:
- Role: Restricted Deterministic Python Execution Sandbox (AST Security Shield)
- Where this file is used / Who calls it:
    1. Called by: src/tools/sandbox_tool.py
       (The ReAct Agent tool invokes SandboxRunner.execute(code) to perform exact calculations).
    2. Used in Agent Reasoning: src/handlers/react_core.py
       (When the Groq Llama-3 ReAct agent issues an Action: "run_financial_math",
        this sandbox executes the code in <10ms inside the agent pod without K8s pod overhead).
    3. Monitored by: observability/langfuse_tracker.py
       (Audits execution time, security blocks, and mathematical calculations for compliance).
=============================================================================
"""

from typing import Any, Dict, Optional, Set
import ast
import io
import math
import sys
import time
import logging
import threading
from contextlib import redirect_stdout

from src.sandbox import formulas

logger = logging.getLogger(__name__)

# Security Policies: Strictly prohibited modules and functions
BANNED_MODULES: Set[str] = {
    "os", "sys", "subprocess", "shutil", "socket", "urllib", "requests", "httpx",
    "pathlib", "importlib", "pty", "posix", "platform", "gc", "signal", "ctypes",
    "inspect", "pickle", "shelve", "tempfile", "builtins", "__builtin__",
}

BANNED_BUILTINS: Set[str] = {
    "eval", "exec", "open", "compile", "__import__", "globals", "locals", "vars",
    "dir", "getattr", "setattr", "delattr", "hasattr", "input", "breakpoint",
    "exit", "quit", "help", "memoryview", "classmethod", "staticmethod",
}

BANNED_ATTRIBUTES: Set[str] = {
    "__subclasses__", "__bases__", "__mro__", "__globals__", "__code__",
    "__builtins__", "__import__", "__class__", "__closure__", "__func__",
}


class SecurityViolationError(Exception):
    """Raised when submitted Python code violates AST security constraints."""
    pass


class CodeSecurityValidator(ast.NodeVisitor):
    """
    AST Visitor to statically inspect Python code before execution.
    Rejects any imports of system modules, calls to dangerous builtins,
    or attempts to navigate dunder attributes for sandbox escape.
    """

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            base_module = alias.name.split(".")[0]
            if base_module in BANNED_MODULES:
                raise SecurityViolationError(f"Security Alert: Import of '{alias.name}' is strictly prohibited.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base_module = node.module.split(".")[0]
            if base_module in BANNED_MODULES:
                raise SecurityViolationError(f"Security Alert: Import from '{node.module}' is strictly prohibited.")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Prevent direct calls to dangerous built-ins (e.g. open(), eval())
        if isinstance(node.func, ast.Name):
            if node.func.id in BANNED_BUILTINS:
                raise SecurityViolationError(f"Security Alert: Function call '{node.func.id}()' is prohibited.")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Prevent dunder escape attempts (e.g., ''.__class__.__mro__[1].__subclasses__())
        if node.attr in BANNED_ATTRIBUTES or (node.attr.startswith("__") and node.attr.endswith("__")):
            raise SecurityViolationError(f"Security Alert: Access to attribute '{node.attr}' is prohibited.")
        self.generic_visit(node)


class SandboxRunner:
    """
    In-process isolated Python execution sandbox for deterministic financial math.
    Executes in <10ms directly inside the Agent pod with AST static verification
    and a 5-second watchdog timer.
    """

    def __init__(self, timeout_seconds: float = 5.0):
        self.timeout_seconds = timeout_seconds

    def _build_safe_environment(self) -> Dict[str, Any]:
        """Constructs a minimal, secure global execution environment."""
        safe_builtins = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "len": len,
            "float": float,
            "int": int,
            "str": str,
            "bool": bool,
            "range": range,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "enumerate": enumerate,
            "zip": zip,
            "pow": pow,
            "divmod": divmod,
            "print": print,
        }

        # Expose math and verified financial formulas
        return {
            "__builtins__": safe_builtins,
            "math": math,
            "dcf": formulas.dcf,
            "wacc": formulas.wacc,
            "cagr": formulas.cagr,
            "pe_ratio": formulas.pe_ratio,
            "free_cash_flow": formulas.free_cash_flow,
            "enterprise_value": formulas.enterprise_value,
            "margin": formulas.margin,
        }

    def execute(self, code: str) -> Dict[str, Any]:
        """
        Statically inspects and executes Python code in a secure sandbox.

        Args:
            code: Python code string generated by LLM Agent.

        Returns:
            Dict containing success boolean, result value, stdout output, error message,
            and execution latency in milliseconds.
        """
        start_time = time.perf_counter()
        stdout_buffer = io.StringIO()

        # Step 1: AST Parsing & Security Validation
        try:
            tree = ast.parse(code)
            validator = CodeSecurityValidator()
            validator.visit(tree)
        except SecurityViolationError as sve:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            logger.warning(f"Sandbox security violation blocked: {sve}")
            return {
                "success": False,
                "result": None,
                "stdout": "",
                "error": str(sve),
                "execution_time_ms": round(latency_ms, 2),
            }
        except SyntaxError as se:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "success": False,
                "result": None,
                "stdout": "",
                "error": f"Python Syntax Error: {se}",
                "execution_time_ms": round(latency_ms, 2),
            }

        # Step 2: Threaded Execution with Watchdog Timeout
        execution_env = self._build_safe_environment()
        local_scope: Dict[str, Any] = {}
        exec_error: List[Exception] = []

        def worker():
            with redirect_stdout(stdout_buffer):
                try:
                    compiled_code = compile(tree, filename="<sandbox>", mode="exec")
                    exec(compiled_code, execution_env, local_scope)
                except Exception as e:
                    exec_error.append(e)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout_seconds)

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if thread.is_alive():
            return {
                "success": False,
                "result": None,
                "stdout": stdout_buffer.getvalue(),
                "error": f"Execution timed out after {self.timeout_seconds} seconds.",
                "execution_time_ms": round(latency_ms, 2),
            }

        if exec_error:
            err = exec_error[0]
            logger.error(f"Sandbox runtime execution error: {err}")
            return {
                "success": False,
                "result": None,
                "stdout": stdout_buffer.getvalue(),
                "error": f"{type(err).__name__}: {str(err)}",
                "execution_time_ms": round(latency_ms, 2),
            }

        # Determine returned output (look for 'result', 'output', or the last variable assigned)
        result_value = local_scope.get("result", local_scope.get("output", None))
        if result_value is None and local_scope:
            # Grab the last assigned user variable
            last_key = list(local_scope.keys())[-1]
            result_value = local_scope[last_key]

        return {
            "success": True,
            "result": result_value,
            "stdout": stdout_buffer.getvalue().strip(),
            "error": None,
            "execution_time_ms": round(latency_ms, 2),
        }


# Singleton runner instance and functional wrapper
sandbox_runner = SandboxRunner()


def run_sandboxed_math(code: str) -> Dict[str, Any]:
    """Convenience functional wrapper to execute math in the sandbox."""
    return sandbox_runner.execute(code)
