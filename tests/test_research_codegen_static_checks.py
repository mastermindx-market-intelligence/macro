"""Fixture tests for the trusted, dormant codegen structural first-pass checker.

Every fixture in this file is a harmless trusted string literal.  No test
compiles, evaluates, executes, or imports a fixture source: the only module
imported is the trusted checker itself.  The checker is expected to inspect
fixture bytes without ever materialising a callable from them, and every
report must be inert (``authority_granted=False``, ``execution_enabled=False``,
``boundary_required=True``).
"""

from __future__ import annotations

import inspect
import json
import unittest
from unittest import mock


from engine.research_codegen import static_checks as CHECKER

check_source = CHECKER.check_source

POSITIVE_FEATURE = """\

def signal(prices, window):
    total = 0.0
    count = 0
    for i in range(window):
        if i < len(prices):
            total = total + prices[i]
            count = count + 1
    if count == 0:
        return 0.0
    return total / count
"""

TINY_ARITHMETIC = "\ndef add2(a, b):\n    return a + b\n"


def _codes(report):
    return sorted(d["code"] for d in report["diagnostics"])


def _assert_inert(self, report):
    self.assertFalse(report["authority_granted"])
    self.assertFalse(report["execution_enabled"])
    self.assertTrue(report["boundary_required"])


class PositiveMorphologyTests(unittest.TestCase):
    def test_tiny_arithmetic_function_accepted(self):
        report = check_source(TINY_ARITHMETIC.encode("utf-8"))
        self.assertEqual(report["disposition"], "accept_morphology")
        self.assertEqual(report["diagnostics"], [])
        _assert_inert(self, report)

    def test_realistic_bounded_feature_accepted(self):
        report = check_source(POSITIVE_FEATURE.encode("utf-8"))
        self.assertEqual(report["disposition"], "accept_morphology")
        self.assertEqual(report["diagnostics"], [])

    def test_report_is_typed_and_json_serialisable(self):
        report = check_source(TINY_ARITHMETIC.encode("utf-8"))
        self.assertEqual(report["schema"], CHECKER.SCHEMA)
        self.assertIsInstance(json.dumps(report), str)
        self.assertEqual(report["limits"], CHECKER.limits())
        for diag in report["diagnostics"]:
            self.assertEqual(
                sorted(diag.keys()), ["code", "col", "line", "message", "severity"]
            )

    def test_deterministic_output(self):
        first = check_source(POSITIVE_FEATURE.encode("utf-8"))
        second = check_source(POSITIVE_FEATURE.encode("utf-8"))
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_no_caller_widening(self):
        signature = inspect.signature(check_source)
        params = list(signature.parameters.values())
        self.assertEqual(len(params), 1)
        self.assertIs(signature.parameters[params[0].name].default, inspect.Parameter.empty)
        self.assertEqual(params[0].kind, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        self.assertEqual(params[0].name, "source")
        self.assertEqual(
            CHECKER.MAX_SOURCE_BYTES, 32 * 1024, "32 KiB ceiling must stay fixed"
        )

    def test_standalone_module_surface(self):
        self.assertEqual(set(CHECKER.__all__), {"SCHEMA", "VERSION", "check_source", "limits"})


class RejectedMorphologyTests(unittest.TestCase):
    def _assert_reject(self, source_text, expected_code=None):
        report = check_source(source_text.encode("utf-8"))
        self.assertEqual(report["disposition"], "reject", source_text)
        self.assertTrue(report["diagnostics"], source_text)
        _assert_inert(self, report)
        if expected_code is not None:
            self.assertIn(expected_code, _codes(report), source_text)
        return report

    def test_import_rejected(self):
        self._assert_reject("import os\n", "disallowed_import")

    def test_from_import_rejected(self):
        self._assert_reject("from math import sqrt\n\ndef f(x):\n    return x\n",
                            "disallowed_import")

    def test_dynamic_execution_rejected(self):
        for snippet in (
            "def f(x):\n    return eval('x')\n",
            "def f(x):\n    exec('x = 1')\n",
            "def f(x):\n    return compile('1', '<s>', 'exec')\n",
            "def f(x):\n    return open('x')\n",
            "def f(x):\n    return __import__('os')\n",
            "def f(x):\n    return getattr(x, 'y')\n",
        ):
            self._assert_reject(snippet, "dynamic_call")

    def test_decorator_rejected(self):
        self._assert_reject("@cache\ndef f(x):\n    return x\n", "disallowed_decorator")

    def test_disallowed_node_types_rejected(self):
        cases = {
            "class": "class C:\n    pass\n",
            "global": "def f(x):\n    global g\n",
            "nonlocal": "def f(x):\n    def g():\n        nonlocal x\n",
            "async": "async def f(x):\n    return x\n",
            "yield": "def f(x):\n    yield x\n",
            "await": "async def f(x):\n    return await g()\n",
            "while": "def f(x):\n    while x:\n        x = x - 1\n",
            "lambda": "def f(x):\n    return (lambda y: y)(x)\n",
            "comprehension": "def f(xs):\n    return [a for a in xs]\n",
            "try": "def f(x):\n    try:\n        return x\n    except ValueError:\n        return 0\n",
            "raise": "def f(x):\n    raise ValueError\n",
            "assert": "def f(x):\n    assert x\n",
            "with": "def f(x):\n    with open('a') as fh:\n        return x\n",
            "walrus": "def f(x):\n    if (y := x):\n        return y\n",
            "fstring": "def f(x):\n    return f'{x}'\n",
            "starred": "def f(xs):\n    return [*xs]\n",
        }
        for label, snippet in cases.items():
            with self.subTest(morphology=label):
                self._assert_reject(snippet)

    def test_attribute_chain_rejected(self):
        self._assert_reject("def f(x):\n    return x.real\n", "disallowed_attribute")

    def test_unknown_name_rejected(self):
        self._assert_reject("def f(x):\n    return undefined_thing\n", "unknown_name")

    def test_module_level_statement_rejected(self):
        self._assert_reject("x = 1\n\ndef f(y):\n    return y\n", "module_level_statement")

    def test_two_feature_functions_rejected(self):
        self._assert_reject("def f(x):\n    return x\n\ndef g(x):\n    return x\n",
                            "multiple_function_definitions")

    def test_negative_literal_index_policy_rejected(self):
        self._assert_reject("def f(a):\n    return a << -1\n", "negative_shift_policy")
        self._assert_reject("def f(a):\n    return a >> -2\n", "negative_shift_policy")
        self._assert_reject("def f(a):\n    return a[-1]\n", "negative_index_policy")
        self._assert_reject("def f(a):\n    return a[:-1]\n", "negative_index_policy")
        self._assert_reject("def f(a):\n    return a[::-1]\n", "negative_index_policy")

    def test_positive_shift_still_accepted(self):
        report = check_source(b"def f(a):\n    return a << 2\n")
        self.assertEqual(report["disposition"], "accept_morphology")

    def test_oversized_integer_literal_rejected(self):
        snippet = "def f(x):\n    return %d\n" % (10 ** 4000,)
        self._assert_reject(snippet, "oversized_literal")

    def test_empty_and_docstring_only_rejected(self):
        for snippet in ("", '"""docstring only"""\n'):
            report = check_source(snippet.encode("utf-8"))
            self.assertEqual(report["disposition"], "reject")
            self.assertIn("no_function_definition", _codes(report))


class RefusalAndResourceTests(unittest.TestCase):
    def test_oversized_bytes_refused_before_decode(self):
        # Invalid UTF-8 AND oversized: only the size refusal may appear,
        # proving the ceiling is applied before any decode or parse.
        payload = b"\xff" * (CHECKER.MAX_SOURCE_BYTES + 1)
        report = check_source(payload)
        self.assertEqual(report["disposition"], "refuse")
        self.assertEqual(_codes(report), ["source_size_limit"])
        self.assertEqual(report["checked_bytes"], len(payload))
        _assert_inert(self, report)

    def test_exact_ceiling_still_processed(self):
        payload = b"\xff" * CHECKER.MAX_SOURCE_BYTES
        report = check_source(payload)
        self.assertNotIn("source_size_limit", _codes(report))

    def test_invalid_utf8_rejected(self):
        report = check_source(b"\xff\xfe\xfd\xfc")
        self.assertEqual(report["disposition"], "reject")
        self.assertEqual(_codes(report), ["invalid_utf8"])

    def test_syntax_error_rejected_deterministically(self):
        first = check_source(b"def f(:\n    pass\n")
        second = check_source(b"def f(:\n    pass\n")
        self.assertEqual(first["disposition"], "reject")
        self.assertIn("syntax_error", _codes(first))
        self.assertEqual(first, second)

    def test_non_bytes_input_refused(self):
        report = check_source("def f():\n    return 1\n")
        self.assertEqual(report["disposition"], "refuse")
        self.assertEqual(_codes(report), ["invalid_input_type"])

    def test_ast_depth_limit_refused(self):
        payload = ("1" + "+1" * 200).encode("utf-8")
        report = check_source(payload)
        self.assertEqual(report["disposition"], "refuse")
        self.assertIn("ast_depth_limit", _codes(report))

    def test_token_limit_refused(self):
        payload = ("def f():\n    return " + "1+" * 4400 + "1\n").encode("utf-8")
        self.assertLess(len(payload), CHECKER.MAX_SOURCE_BYTES)
        report = check_source(payload)
        self.assertEqual(report["disposition"], "refuse")
        self.assertIn("token_limit", _codes(report))

    def test_nesting_limit_refused(self):
        payload = ("def f():\n    return " + "(" * 40 + "1" + ")" * 40 + "\n").encode("utf-8")
        report = check_source(payload)
        self.assertEqual(report["disposition"], "refuse")
        self.assertIn("preparse_nesting_limit", _codes(report))

    def test_embedded_null_byte_is_deterministic(self):
        first = check_source(b"def f():\n    return 1\x00\n")
        second = check_source(b"def f():\n    return 1\x00\n")
        self.assertIn(first["disposition"], ("reject", "refuse"))
        self.assertEqual(first, second)


class BindingAndContextTests(unittest.TestCase):
    """Small, fixed morphology fixtures; parsing only, never execution."""

    def test_reserved_bindings_are_rejected_in_all_binding_positions(self):
        for source in (
            "def f(len):\n    return len\n",
            "def f(x):\n    abs = 1\n    return abs\n",
            "def sum(x):\n    return x\n",
            "def f(xs):\n    for max in xs:\n        pass\n    return 1\n",
            "def f(list):\n    return list\n",
        ):
            with self.subTest(source=source):
                report = check_source(source.encode())
                self.assertIn("reserved_binding", _codes(report))
                self.assertEqual(report["disposition"], "reject")
                _assert_inert(self, report)

    def test_one_function_means_one_definition_in_the_entire_module(self):
        report = check_source(b"def f(x):\n    def g(y):\n        return y\n    return x\n")
        self.assertIn("nested_function", _codes(report))

    def test_loop_target_and_iteration_input_contract(self):
        cases = (
            ("def f(xs):\n    for a, b in xs:\n        pass\n    return 1\n", "disallowed_target"),
            ("def f(xs):\n    for xs[0] in xs:\n        pass\n    return 1\n", "disallowed_target"),
            ("def f(xs):\n    ys = [1]\n    for y in ys:\n        pass\n    return 1\n", "disallowed_iteration_source"),
            ("def f(xs):\n    xs = [1]\n    return xs\n", "input_rebinding"),
        )
        for source, code in cases:
            with self.subTest(code=code):
                self.assertIn(code, _codes(check_source(source.encode())))
        report = check_source(b"def f(xs):\n    total = 0\n    for x in xs:\n        total += x\n    return total\n")
        self.assertEqual(report["disposition"], "accept_morphology")

    def test_dictionary_unpack_is_rejected(self):
        self.assertIn("dict_unpack", _codes(check_source(b"def f(x):\n    return {**x}\n")))

    def test_annotation_context_does_not_grant_value_or_call_permissions(self):
        report = check_source(b"def f(xs: list) -> float:\n    ys: list = xs\n    return 1.0\n")
        self.assertEqual(report["disposition"], "accept_morphology")
        for source in (
            "def f(xs: len(1)):\n    return xs\n",
            "def f(xs) -> len(1):\n    return xs\n",
            "def f(xs):\n    ys: list[int] = xs\n    return ys\n",
        ):
            self.assertIn("disallowed_annotation", _codes(check_source(source.encode())))
        self.assertIn("unknown_name", _codes(check_source(b"def f(xs: list):\n    return list\n")))

    def test_loop_control_uses_loop_body_context(self):
        for source in (
            "def f(x):\n    break\n",
            "def f(x):\n    continue\n",
            "def f(xs):\n    for x in xs:\n        pass\n    else:\n        break\n",
        ):
            self.assertIn("loop_control_context", _codes(check_source(source.encode())))
        report = check_source(b"def f(xs):\n    for x in xs:\n        if x:\n            break\n    return 1\n")
        self.assertEqual(report["disposition"], "accept_morphology")

    def test_duplicate_parameters_and_nonfinite_literals_rejected(self):
        self.assertIn("duplicate_parameter", _codes(check_source(b"def f(x, x):\n    return x\n")))
        self.assertIn("nonfinite_literal", _codes(check_source(b"def f(x):\n    return 1e999\n")))

    def test_mocked_resource_failures_refuse_at_each_inspection_stage(self):
        stages = (
            (CHECKER.tokenize, "generate_tokens", "inspection_failure"),
            (CHECKER.ast, "parse", "parser_failure"),
            (CHECKER, "_iter_stack", "inspection_failure"),
            (CHECKER, "_check_semantics", "inspection_failure"),
        )
        for owner, name, code in stages:
            for exception in (MemoryError, RecursionError, OverflowError):
                with self.subTest(stage=name, error=exception.__name__):
                    with mock.patch.object(owner, name, side_effect=exception):
                        report = check_source(TINY_ARITHMETIC.encode())
                    self.assertEqual(report["disposition"], "refuse")
                    self.assertIn(code, _codes(report))
                    _assert_inert(self, report)

    def test_bytes_subclass_is_refused_without_dispatching_decode(self):
        class CustomBytes(bytes):
            def decode(self, *args, **kwargs):
                raise AssertionError("must not invoke caller-defined methods")
        report = check_source(CustomBytes(b"ignored"))
        self.assertEqual(_codes(report), ["invalid_input_type"])


if __name__ == "__main__":
    unittest.main()
