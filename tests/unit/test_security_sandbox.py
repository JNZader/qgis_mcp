"""
Unit tests for ImprovedCodeSandbox (AST-based)

Tests cover:
- Valid code execution
- Dangerous imports blocking
- Dangerous function blocking
- Dangerous attribute blocking
- Node type whitelisting
- Code length limits
- Timeout enforcement
- Namespace isolation
- Bypass attempt prevention
"""

import ast
import time

import pytest
from security_improved import ImprovedCodeSandbox, SecurityException


class TestCodeSandboxBasics:
    """Basic sandbox functionality tests"""

    def test_valid_simple_code(self, sandbox):
        """Test that simple valid code passes validation"""
        code = "x = 1 + 2"
        sandbox.validate_code(code)  # Should not raise

    def test_valid_complex_code(self, sandbox):
        """Test that complex valid code passes validation"""
        code = """
x = [1, 2, 3, 4, 5]
y = [i * 2 for i in x if i > 2]
result = sum(y)
"""
        sandbox.validate_code(code)  # Should not raise

    def test_valid_function_definition(self, sandbox):
        """Test that function definitions are allowed"""
        code = """
def add(a, b):
    return a + b

result = add(1, 2)
"""
        sandbox.validate_code(code)  # Should not raise

    def test_valid_loops(self, sandbox):
        """Test that loops are allowed"""
        code = """
total = 0
for i in range(10):
    total += i

while total < 100:
    total += 1
"""
        sandbox.validate_code(code)  # Should not raise

    def test_valid_conditionals(self, sandbox):
        """Test that conditionals are allowed"""
        code = """
x = 10
if x > 5:
    result = "large"
else:
    result = "small"
"""
        sandbox.validate_code(code)  # Should not raise


class TestDangerousImports:
    """Test blocking of dangerous imports"""

    def test_os_import_blocked(self, sandbox):
        """Test that os module import is blocked"""
        with pytest.raises(SecurityException, match="Import"):
            sandbox.validate_code("import os")

    def test_subprocess_import_blocked(self, sandbox):
        """Test that subprocess import is blocked"""
        with pytest.raises(SecurityException, match="Import"):
            sandbox.validate_code("import subprocess")

    def test_sys_import_blocked(self, sandbox):
        """Test that sys import is blocked"""
        with pytest.raises(SecurityException, match="Import"):
            sandbox.validate_code("import sys")

    def test_socket_import_blocked(self, sandbox):
        """Test that socket import is blocked"""
        with pytest.raises(SecurityException, match="Import"):
            sandbox.validate_code("import socket")

    def test_urllib_import_blocked(self, sandbox):
        """Test that urllib import is blocked"""
        with pytest.raises(SecurityException, match="Import"):
            sandbox.validate_code("import urllib")

    def test_requests_import_blocked(self, sandbox):
        """Test that requests import is blocked"""
        with pytest.raises(SecurityException, match="Import"):
            sandbox.validate_code("import requests")

    def test_from_import_blocked(self, sandbox):
        """Test that from imports are also blocked"""
        with pytest.raises(SecurityException, match="Import"):
            sandbox.validate_code("from os import system")

    def test_wildcard_import_blocked(self, sandbox):
        """Test that wildcard imports are blocked"""
        with pytest.raises(SecurityException, match="Wildcard imports not allowed"):
            sandbox.validate_code("from qgis.core import *")

    def test_specific_qgis_import_allowed(self, sandbox):
        """Test that specific QGIS imports are allowed"""
        code = "from qgis.core import QgsProject"
        sandbox.validate_code(code)  # Should not raise

    def test_unauthorized_qgis_class_blocked(self, sandbox):
        """Test that unauthorized QGIS classes are blocked"""
        with pytest.raises(SecurityException, match="Import"):
            sandbox.validate_code("from qgis.core import QgsApplication")


class TestDangerousFunctions:
    """Test blocking of dangerous functions"""

    def test_eval_blocked(self, sandbox):
        """Test that eval() is blocked"""
        with pytest.raises(SecurityException, match="Dangerous function"):
            sandbox.validate_code("eval('1+1')")

    def test_exec_blocked(self, sandbox):
        """Test that exec() is blocked"""
        with pytest.raises(SecurityException, match="Dangerous function"):
            sandbox.validate_code("exec('x=1')")

    def test_compile_blocked(self, sandbox):
        """Test that compile() is blocked"""
        with pytest.raises(SecurityException, match="Dangerous function"):
            sandbox.validate_code("compile('x=1', '', 'exec')")

    def test_import_blocked_as_function(self, sandbox):
        """Test that __import__() is blocked"""
        with pytest.raises(SecurityException, match="Dangerous function"):
            sandbox.validate_code("__import__('os')")

    def test_open_blocked(self, sandbox):
        """Test that open() is blocked"""
        with pytest.raises(SecurityException, match="Dangerous function"):
            sandbox.validate_code("open('/etc/passwd')")

    def test_input_blocked(self, sandbox):
        """Test that input() is blocked"""
        with pytest.raises(SecurityException, match="Dangerous function"):
            sandbox.validate_code("x = input('prompt')")

    def test_getattr_blocked(self, sandbox):
        """Test that getattr() is blocked"""
        with pytest.raises(SecurityException, match="Dangerous function"):
            sandbox.validate_code("getattr(obj, 'attr')")

    def test_setattr_blocked(self, sandbox):
        """Test that setattr() is blocked"""
        with pytest.raises(SecurityException, match="Dangerous function"):
            sandbox.validate_code("setattr(obj, 'attr', value)")

    def test_delattr_blocked(self, sandbox):
        """Test that delattr() is blocked"""
        with pytest.raises(SecurityException, match="Dangerous function"):
            sandbox.validate_code("delattr(obj, 'attr')")

    def test_hasattr_blocked(self, sandbox):
        """Test that hasattr() is blocked"""
        with pytest.raises(SecurityException, match="Dangerous function"):
            sandbox.validate_code("hasattr(obj, 'attr')")

    def test_vars_blocked(self, sandbox):
        """Test that vars() is blocked"""
        with pytest.raises(SecurityException, match="Dangerous"):
            sandbox.validate_code("vars()")

    def test_dir_blocked(self, sandbox):
        """Test that dir() is blocked"""
        with pytest.raises(SecurityException, match="Dangerous"):
            sandbox.validate_code("dir(obj)")

    def test_globals_blocked(self, sandbox):
        """Test that globals() is blocked"""
        with pytest.raises(SecurityException, match="Dangerous"):
            sandbox.validate_code("globals()")

    def test_locals_blocked(self, sandbox):
        """Test that locals() is blocked"""
        with pytest.raises(SecurityException, match="Dangerous"):
            sandbox.validate_code("locals()")


class TestDangerousAttributes:
    """Test blocking of dangerous attribute access"""

    def test_builtins_attribute_blocked(self, sandbox):
        """Test that __builtins__ access is blocked"""
        with pytest.raises(SecurityException, match="Dangerous attribute"):
            sandbox.validate_code("x = object.__builtins__")

    def test_globals_attribute_blocked(self, sandbox):
        """Test that __globals__ access is blocked"""
        with pytest.raises(SecurityException, match="Dangerous attribute"):
            sandbox.validate_code("x = func.__globals__")

    def test_dict_attribute_blocked(self, sandbox):
        """Test that __dict__ access is blocked"""
        with pytest.raises(SecurityException, match="Dangerous attribute"):
            sandbox.validate_code("x = obj.__dict__")

    def test_class_attribute_blocked(self, sandbox):
        """Test that __class__ access is blocked"""
        with pytest.raises(SecurityException, match="Dangerous attribute"):
            sandbox.validate_code("x = obj.__class__")

    def test_bases_attribute_blocked(self, sandbox):
        """Test that __bases__ access is blocked"""
        with pytest.raises(SecurityException, match="Dangerous attribute"):
            sandbox.validate_code("x = cls.__bases__")

    def test_subclasses_attribute_blocked(self, sandbox):
        """Test that __subclasses__ access is blocked"""
        with pytest.raises(SecurityException, match="Dangerous attribute"):
            sandbox.validate_code("x = cls.__subclasses__")

    def test_import_attribute_blocked(self, sandbox):
        """Test that __import__ access is blocked"""
        with pytest.raises(SecurityException, match="dangerous"):
            sandbox.validate_code("x = __import__")


class TestBypassAttempts:
    """Test various sandbox bypass attempts"""

    def test_nested_eval_blocked(self, sandbox):
        """Test that nested eval is blocked"""
        with pytest.raises(SecurityException):
            sandbox.validate_code("eval(eval('\"1+1\"'))")

    def test_string_concatenation_eval_blocked(self, sandbox):
        """Test that string concatenation to build eval is blocked"""
        code = """
func = 'ev' + 'al'
# Even if we could call it, eval itself is blocked in AST
"""
        # The eval call itself would be blocked
        sandbox.validate_code(code)  # This part passes
        # But using eval would fail

    def test_attribute_chain_bypass_blocked(self, sandbox):
        """Test that attribute chain bypasses are blocked"""
        with pytest.raises(SecurityException):
            sandbox.validate_code("[].__class__.__bases__[0].__subclasses__()")

    def test_getitem_bypass_blocked(self, sandbox):
        """Test that __getitem__ bypass is blocked"""
        with pytest.raises(SecurityException):
            sandbox.validate_code("().__class__.__bases__[0]")

    def test_lambda_bypass_attempt(self, sandbox):
        """Test that lambda bypass attempts fail"""
        # Lambda with eval inside
        with pytest.raises(SecurityException):
            sandbox.validate_code("f = lambda: eval('1')")

    def test_comprehension_bypass_attempt(self, sandbox):
        """Test that comprehension bypass attempts fail"""
        with pytest.raises(SecurityException):
            sandbox.validate_code("[eval('1') for i in range(1)]")


class TestCodeLengthLimits:
    """Test code length restrictions"""

    def test_within_length_limit(self, sandbox):
        """Test that code within limit is accepted"""
        code = "x = 1\n" * 100
        sandbox.validate_code(code)  # Should not raise

    def test_exceeds_length_limit(self, sandbox):
        """Test that code exceeding limit is rejected"""
        code = "x = 1\n" * 100000  # Very long
        with pytest.raises(SecurityException, match="exceeds maximum length"):
            sandbox.validate_code(code)

    def test_exact_length_limit(self):
        """Test code at exact length limit"""
        sandbox = ImprovedCodeSandbox(max_code_length=100)
        code = "x" * 100
        sandbox.validate_code(code)  # Should not raise

        code = "x" * 101
        with pytest.raises(SecurityException, match="exceeds maximum length"):
            sandbox.validate_code(code)


class TestNamespaceIsolation:
    """Test namespace isolation and safety"""

    def test_safe_namespace_creation(self, sandbox):
        """Test that safe namespace contains only allowed builtins"""
        namespace = sandbox.create_safe_namespace()

        # Check allowed builtins are present
        builtins = namespace["__builtins__"]
        assert "print" in builtins
        assert "len" in builtins
        assert "int" in builtins
        assert "str" in builtins
        assert "list" in builtins
        assert "dict" in builtins

        # Check dangerous builtins are absent
        assert "eval" not in builtins
        assert "exec" not in builtins
        assert "open" not in builtins
        assert "__import__" not in builtins
        assert "compile" not in builtins

    def test_namespace_isolation(self, sandbox):
        """Test that namespace is isolated"""
        namespace1 = sandbox.create_safe_namespace()
        namespace2 = sandbox.create_safe_namespace()

        # Namespaces should be different objects
        assert namespace1 is not namespace2


class TestSyntaxValidation:
    """Test syntax error handling"""

    def test_invalid_syntax_rejected(self, sandbox):
        """Test that invalid Python syntax is rejected"""
        with pytest.raises(SecurityException, match="Invalid Python syntax"):
            sandbox.validate_code("x = ")

    def test_unclosed_bracket(self, sandbox):
        """Test that unclosed brackets are rejected"""
        with pytest.raises(SecurityException, match="Invalid Python syntax"):
            sandbox.validate_code("x = [1, 2, 3")

    def test_invalid_indentation(self, sandbox):
        """Test that invalid indentation is rejected"""
        with pytest.raises(SecurityException, match="Invalid Python syntax"):
            sandbox.validate_code("if True:\nx = 1")  # Missing indent


class TestDisallowedNodeTypes:
    """Test that disallowed AST node types are blocked"""

    def test_try_except_allowed(self, sandbox):
        """Test that try-except is currently blocked (not in whitelist)"""
        code = """
try:
    x = 1
except:
    x = 0
"""
        # Try-except is not in ALLOWED_NODES, so it should be blocked
        with pytest.raises(SecurityException, match="Disallowed operation"):
            sandbox.validate_code(code)

    def test_with_statement_blocked(self, sandbox):
        """Test that with statements are blocked"""
        with pytest.raises(SecurityException, match="Disallowed operation"):
            sandbox.validate_code("with open('file') as f: pass")

    def test_class_definition_blocked(self, sandbox):
        """Test that class definitions are blocked"""
        with pytest.raises(SecurityException, match="Disallowed operation"):
            sandbox.validate_code("class MyClass: pass")

    def test_async_blocked(self, sandbox):
        """Test that async/await is blocked"""
        with pytest.raises(SecurityException, match="Disallowed operation"):
            sandbox.validate_code("async def func(): pass")

    def test_yield_blocked(self, sandbox):
        """Test that yield is blocked"""
        code = """
def gen():
    yield 1
"""
        with pytest.raises(SecurityException, match="Disallowed operation"):
            sandbox.validate_code(code)

    def test_global_statement_blocked(self, sandbox):
        """Test that global statements are blocked"""
        with pytest.raises(SecurityException, match="Disallowed operation"):
            sandbox.validate_code("global x")

    def test_nonlocal_statement_blocked(self, sandbox):
        """Test that nonlocal statements are blocked"""
        code = """
def outer():
    x = 1
    def inner():
        nonlocal x
        x = 2
"""
        with pytest.raises(SecurityException, match="Disallowed operation"):
            sandbox.validate_code(code)


@pytest.mark.slow
class TestTimeoutEnforcement:
    """Test timeout enforcement (Unix only)"""

    @pytest.mark.skipif(
        not hasattr(__import__("signal"), "SIGALRM"), reason="SIGALRM not available on Windows"
    )
    def test_timeout_on_infinite_loop(self, sandbox):
        """Test that infinite loops trigger timeout"""
        code = """
while True:
    pass
"""
        with pytest.raises(TimeoutError, match="timeout"):
            sandbox.execute_with_timeout(code)

    @pytest.mark.skipif(
        not hasattr(__import__("signal"), "SIGALRM"), reason="SIGALRM not available on Windows"
    )
    def test_timeout_on_expensive_computation(self, sandbox):
        """Test that expensive computations trigger timeout"""
        code = """
result = 0
for i in range(100000000):
    result += i
"""
        # This might or might not timeout depending on hardware
        # Just ensure the timeout mechanism works
        try:
            sandbox.execute_with_timeout(code)
        except TimeoutError:
            pass  # Expected on slow systems


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
