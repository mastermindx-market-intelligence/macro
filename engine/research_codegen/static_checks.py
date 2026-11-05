"""Trusted, pure, dormant structural first-pass checker for Research Factory codegen.

WHAT THIS MODULE IS
===================
A stdlib-only, deterministic, side-effect-free *syntax and morphology* gate for
candidate feature sources submitted to the Research Factory codegen programme.
``check_source(source: bytes)`` returns an inert, JSON-serialisable, typed
diagnostic report.  It never executes, imports, compiles, or materialises
anything from the supplied source.  ``ast.parse`` is used for syntax
inspection only; no callable object, code object, or module object is ever
created from the input.

WHAT THIS MODULE IS NOT
=======================
This is a first-pass *linter*, not a sandbox and not a security boundary.

* It cannot detect all channels of future (look-ahead) information.
* It cannot prevent hostile execution.  A module-level check cannot prove
  physical resource safety of the parser itself for untrusted input.
* Physical containment (process/network/filesystem isolation, CPU, memory and
  wall-clock budgets) and per-decision prefix-only input handling remain
  mandatory duties of the eventual isolated caller.

Accordingly every report carries ``authority_granted = False``,
``execution_enabled = False`` and ``boundary_required = True``.  A report is
advisory input to the integrating parent; it is never an acceptance receipt,
an activation key, or a scientific result.

SYNTAX ASSUMPTIONS (APPROVED MORPHOLOGY, v1)
============================================
The only accepted shape is deliberately tiny and explicit:

* One module, containing an optional docstring and **exactly one** plain
  ``def`` feature function (no ``async def``).
* Inside that function: restricted arithmetic and iteration syntax only.
  Syntax limits do not bound arithmetic cost, iteration count or allocations.
* Expressions: int/float/bool/str/None constants (bytes and f-strings
  rejected), plain names, ``+ - * / // % ** << >>``, unary ``+ - not``,
  ``and or``, comparisons (``== != < <= > >= in not in``), conditional
  expressions, tuple/list/dict displays, read-only subscripts and slices.
* Calls: only positional-argument calls of a fixed builtin whitelist
  (``range len min max abs round int float bool str sum``).  Every other
  call -- including any call through an attribute -- is rejected.
* Statements inside the function: assignment / annotated assignment /
  augmented assignment to a plain local name, ``if``/``elif``/``else``,
  ``for`` over ``range(...)`` or a plain input name, ``return``, ``pass``,
  ``break``, ``continue``.
* Rejected outright: every import, every decorator, ``class``,
  ``global``/``nonlocal``, ``async``/``await``/``yield``, ``while``
  (unbounded loop), ``try``/``with``/``raise``/``assert``/``del``,
  comprehensions, lambdas, walrus, starred forms, keyword arguments,
  attribute access of any kind, dynamic names (``eval``/``exec``/
  ``compile``/``open``/``__import__``/``getattr``/``globals``/...),
  nested functions, and any module-level executable statement other than
  the docstring and the single feature function.
* Callable and annotation builtin names may not be rebound. Inputs may not
  be rebound. Annotations, where present, are single fixed primitive names.
* Negative literal shift operands and subscript/slice bounds are rejected
  by a conservative syntax policy. Python bit shifts have no time meaning;
  a negative index into a past-only prefix is not inherently look-ahead.
  This policy proves no temporal property of the input or calculation.
* Load of a name that is neither a local (parameter, assigned, or loop
  target) nor a whitelisted builtin is rejected as ``unknown_name``.

The morphology is fixed in this module version.  Callers cannot widen it:
no parameter, keyword, environment variable, or configuration file feeds
any limit or rule below.

RESOURCE DISCIPLINE
===================
* The 32 KiB bytes ceiling is enforced *before* UTF-8 decoding or parsing.
* A conservative token-count and bracket-nesting bound is applied with
  ``tokenize`` (outside strings) before ``ast.parse``; a tokenize failure
  combined with a parse success is refused as ``preparse_unverified``.
* Observed parser/decoder/inspection failures (recursion, memory, int literals under
  CPython 3.11's int/str limit, embedded NUL, ...) map to a deterministic
  ``refuse`` disposition where the process can still construct a report.
  A real process kill or exhausted allocator still needs the external boundary.
* The AST walk is iterative (explicit stack, no recursion) with fixed node
  count and depth ceilings.

Version: 1 (v1).  Schema: ``mastermind.research_codegen.static_checks.v1``.
"""

from __future__ import annotations

import ast
import io
import math
import tokenize

__all__ = ["SCHEMA", "VERSION", "check_source", "limits"]

SCHEMA = "mastermind.research_codegen.static_checks.v1"
VERSION = 1

# ---------------------------------------------------------------------------
# Fixed limits.  Not configurable by callers, by design.
# ---------------------------------------------------------------------------
MAX_SOURCE_BYTES = 32 * 1024  # 32 KiB, checked before any decode/parse
MAX_TOKENS = 8192
MAX_NESTING_DEPTH = 32  # bracket nesting outside string literals
MAX_AST_NODES = 20000
MAX_AST_DEPTH = 64
MAX_CALL_ARGS = 8
MAX_INT_BITS = 2048  # conservative literal-magnitude ceiling

DISPOSITION_ACCEPT = "accept_morphology"
DISPOSITION_REJECT = "reject"
DISPOSITION_REFUSE = "refuse"

# Builtin names callable by a candidate.  Nothing else is callable in v1.
CALL_WHITELIST = frozenset(
    {"range", "len", "min", "max", "abs", "round", "int", "float", "bool", "str", "sum"}
)

# Names that must never be resolved even as non-called references.
FORBIDDEN_NAMES = frozenset(
    {
        "eval", "exec", "compile", "open", "__import__", "getattr", "setattr",
        "delattr", "globals", "locals", "vars", "input", "breakpoint", "help",
        "memoryview", "bytearray", "type", "super", "dir", "__builtins__",
    }
)

ALLOWED_ANNOTATIONS = frozenset({"int", "float", "bool", "str", "list", "dict", "tuple"})

# AST node class names permitted anywhere in the tree.
_ALLOWED_NODES = frozenset(
    {
        # containers / definitions
        "Module", "FunctionDef", "arguments", "arg",
        # statements
        "Expr", "Assign", "AnnAssign", "AugAssign", "If", "For", "Return",
        "Pass", "Break", "Continue",
        # expressions
        "Constant", "Name", "BinOp", "UnaryOp", "BoolOp", "Compare", "IfExp",
        "Tuple", "List", "Dict", "Subscript", "Slice", "Call",
        # load/store context markers
        "Load", "Store",
        # operators
        "Add", "Sub", "Mult", "Div", "FloorDiv", "Mod", "Pow", "LShift", "RShift",
        "USub", "UAdd", "Not", "And", "Or",
        "Eq", "NotEq", "Lt", "LtE", "Gt", "GtE", "In", "NotIn",
    }
)

_SHIFT_OPS = frozenset({"LShift", "RShift"})
_OPEN_BRACKETS = {"(": 1, "[": 1, "{": 1}
_CLOSE_BRACKETS = {")": -1, "]": -1, "}": -1}

ASSUMPTIONS = (
    "v1 approved morphology: one module docstring plus exactly one plain def",
    "restricted arithmetic and for-iteration syntax; no workload bound is proven",
    "imports, decorators, classes, async/yield, attributes and dynamic calls are rejected",
    "negative literal shifts/indices are a syntax policy, not a look-ahead detector",
)

LIMITATIONS = (
    "static first pass only; does not detect all future-information channels",
    "does not prevent hostile execution; physical containment remains caller duty",
    "cannot prove parser resource safety for untrusted input; isolated caller with "
    "external CPU/memory/time budgets is required",
    "per-decision prefix-only input handling remains caller duty",
    "compile validity, runtime types and workload bounds remain unqualified",
    "an accept disposition is advisory, not an acceptance receipt or activation key",
)


def limits() -> dict:
    """Return the fixed, non-configurable limits applied by this module."""
    return {
        "max_source_bytes": MAX_SOURCE_BYTES,
        "max_tokens": MAX_TOKENS,
        "max_nesting_depth": MAX_NESTING_DEPTH,
        "max_ast_nodes": MAX_AST_NODES,
        "max_ast_depth": MAX_AST_DEPTH,
        "max_call_args": MAX_CALL_ARGS,
        "max_int_bits": MAX_INT_BITS,
    }


def _diagnostic(code: str, severity: str, message: str, line: int = 0, col: int = 0) -> dict:
    return {"code": code, "severity": severity, "message": message, "line": line, "col": col}


def _empty_report(checked_bytes: int) -> dict:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "disposition": DISPOSITION_REJECT,
        "authority_granted": False,
        "execution_enabled": False,
        "boundary_required": True,
        "checked_bytes": checked_bytes,
        "diagnostics": [],
        "limits": limits(),
        "assumptions": list(ASSUMPTIONS),
        "limitations": list(LIMITATIONS),
    }


def _finalise(report: dict, diagnostics: list) -> dict:
    """Deterministic disposition + sorted diagnostics; always inert flags."""
    deduped = sorted(
        {tuple(sorted(d.items())) for d in diagnostics},
        key=lambda items: (
            [v for k, v in items if k == "code"][0],
            [v for k, v in items if k == "line"][0],
            [v for k, v in items if k == "col"][0],
            [v for k, v in items if k == "message"][0],
        ),
    )
    report["diagnostics"] = [dict(items) for items in deduped]
    codes = {d["code"] for d in report["diagnostics"]}
    severities = {d["severity"] for d in report["diagnostics"]}
    if "refuse" in severities:
        report["disposition"] = DISPOSITION_REFUSE
    elif severities or codes:
        report["disposition"] = DISPOSITION_REJECT
    else:
        report["disposition"] = DISPOSITION_ACCEPT
    return report


def _iter_stack(root: ast.AST):
    """Iterative (node, depth) walk. No recursion, fixed-order children."""
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        yield node, depth
        child_depth = depth + 1
        for child in ast.iter_child_nodes(node):
            stack.append((child, child_depth))


def _preparse_bounds(text: str, diagnostics: list) -> tuple:
    """Tokenize-based conservative bound check.

    Returns ``(bounds_ok, tokenize_failed)``.  ``bounds_ok=False`` means a
    fixed ceiling was exceeded and the caller must refuse.  A tokenize syntax
    failure is *not* itself a verdict (``ast.parse`` owns the canonical syntax
    decision); the caller only refuses as ``preparse_unverified`` if tokenize
    failed *and* the source nevertheless parses.
    """
    count = 0
    depth = 0
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            count += 1
            if count > MAX_TOKENS:
                diagnostics.append(
                    _diagnostic("token_limit", "refuse", "token count exceeds fixed ceiling")
                )
                return False, False
            if tok.type == tokenize.OP:
                t = tok.string
                depth += _OPEN_BRACKETS.get(t, 0) + _CLOSE_BRACKETS.get(t, 0)
                if depth > MAX_NESTING_DEPTH:
                    diagnostics.append(
                        _diagnostic(
                            "preparse_nesting_limit",
                            "refuse",
                            "bracket nesting exceeds fixed ceiling",
                        )
                    )
                    return False, False
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        return True, True  # not a verdict; parse decides
    return True, False


def _is_negative_constant(expr: ast.AST) -> bool:
    """True for a literal negative integer (``-3`` or ``-0``), else False."""
    if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.USub):
        operand = expr.operand
        return isinstance(operand, ast.Constant) and isinstance(operand.value, int)
    return isinstance(expr, ast.Constant) and isinstance(expr.value, int) and expr.value < 0


def _check_index_policy(node: ast.AST, diagnostics: list) -> None:
    """Conservative syntax policy; neither bit shifts nor indices prove time."""
    if isinstance(node, ast.BinOp) and type(node.op).__name__ in _SHIFT_OPS:
        if _is_negative_constant(node.right):
            diagnostics.append(
                _diagnostic(
                    "negative_shift_policy",
                    "reject",
                    "negative literal shift operand is outside the syntax policy",
                    getattr(node, "lineno", 0),
                    getattr(node, "col_offset", 0),
                )
            )
    elif isinstance(node, ast.Subscript):
        sl = node.slice
        if isinstance(sl, ast.Slice):
            for part in (sl.lower, sl.upper, sl.step):
                if part is not None and _is_negative_constant(part):
                    diagnostics.append(
                        _diagnostic(
                            "negative_index_policy",
                            "reject",
                            "negative literal slice bound is outside the syntax policy",
                            getattr(node, "lineno", 0),
                            getattr(node, "col_offset", 0),
                        )
                    )
        elif _is_negative_constant(sl):
            diagnostics.append(
                _diagnostic(
                    "negative_index_policy",
                    "reject",
                    "negative literal subscript index is outside the syntax policy",
                    getattr(node, "lineno", 0),
                    getattr(node, "col_offset", 0),
                )
            )


def _collect_locals(func: ast.FunctionDef) -> set:
    """Collect parameter names and store targets within the single function."""
    local_names = set()
    a = func.args
    for a_node in list(a.posonlyargs) + list(a.args):
        local_names.add(a_node.arg)
    for stmt in ast.walk(func):  # node count already bounded by pass C
        if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            for target in targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Name):
                        local_names.add(sub.id)
        elif isinstance(stmt, ast.For):
            for sub in ast.walk(stmt.target):
                if isinstance(sub, ast.Name):
                    local_names.add(sub.id)
    return local_names


def _check_bindings_and_context(tree: ast.Module, funcs: list, diagnostics: list) -> set:
    """Validate fixed bindings and statement contexts, without compilation.

    Return only the identities of valid annotation Name nodes; a type name is
    permitted in annotation context without becoming a value/call permission.
    """
    annotation_names = set()
    reserved = CALL_WHITELIST | ALLOWED_ANNOTATIONS | FORBIDDEN_NAMES
    inputs = {arg.arg for func in funcs
              for arg in (*func.args.posonlyargs, *func.args.args)}

    def reject(node, code, message):
        diagnostics.append(_diagnostic(code, "reject", message,
                                       getattr(node, "lineno", 0),
                                       getattr(node, "col_offset", 0)))

    for node, _ in _iter_stack(tree):
        binding = None
        if isinstance(node, ast.FunctionDef):
            binding = node.name
            if node not in funcs:
                reject(node, "nested_function", "nested function definitions are rejected")
            args = [a.arg for a in (*node.args.posonlyargs, *node.args.args)]
            if len(args) != len(set(args)):
                reject(node, "duplicate_parameter", "parameter names must be unique")
        elif isinstance(node, ast.arg):
            binding = node.arg
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            binding = node.id
            if binding in inputs:
                reject(node, "input_rebinding", "input parameter names may not be rebound")
        if binding in reserved:
            reject(node, "reserved_binding", "builtin and forbidden names may not be rebound")

        annotation = None
        if isinstance(node, (ast.arg, ast.AnnAssign)):
            annotation = node.annotation
        elif isinstance(node, ast.FunctionDef):
            annotation = node.returns
        if annotation is not None:
            if isinstance(annotation, ast.Name) and annotation.id in ALLOWED_ANNOTATIONS:
                annotation_names.add(id(annotation))
            else:
                reject(annotation, "disallowed_annotation",
                       "annotations must be a single approved builtin type name")

        if isinstance(node, ast.Dict) and any(key is None for key in node.keys):
            reject(node, "dict_unpack", "dictionary unpacking is rejected")
        if isinstance(node, ast.For):
            if not isinstance(node.target, ast.Name):
                reject(node.target, "disallowed_target", "loop targets must be plain local names")
            if isinstance(node.iter, ast.Name) and node.iter.id not in inputs:
                reject(node.iter, "disallowed_iteration_source",
                       "named iteration sources must be declared inputs")

    # Track loop bodies structurally. A loop's else suite does not inherit that
    # loop as an active break/continue target; an enclosing loop still applies.
    pending = [(stmt, 0) for func in funcs for stmt in func.body]
    while pending:
        stmt, loop_depth = pending.pop()
        if isinstance(stmt, (ast.Break, ast.Continue)) and not loop_depth:
            reject(stmt, "loop_control_context", "break/continue requires an enclosing loop body")
        if isinstance(stmt, ast.For):
            pending.extend((child, loop_depth + 1) for child in stmt.body)
            pending.extend((child, loop_depth) for child in stmt.orelse)
        elif isinstance(stmt, ast.If):
            pending.extend((child, loop_depth) for child in (*stmt.body, *stmt.orelse))
    return annotation_names


def _check_semantics(tree: ast.Module, diagnostics: list) -> None:
    """Whitelist morphology checks. Iterative; tree already size-bounded."""
    funcs = [s for s in tree.body if isinstance(s, ast.FunctionDef)]
    if not funcs:
        diagnostics.append(
            _diagnostic("no_function_definition", "reject", "no feature function definition found")
        )
    if len(funcs) > 1:
        diagnostics.append(
            _diagnostic(
                "multiple_function_definitions",
                "reject",
                "v1 morphology allows exactly one feature function",
            )
        )
    for stmt in tree.body:
        if isinstance(stmt, ast.FunctionDef):
            continue
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            diagnostics.append(
                _diagnostic(
                    "disallowed_import",
                    "reject",
                    "imports are disallowed in v1; the candidate is source-only and "
                    "dependency-free",
                    getattr(stmt, "lineno", 0),
                    getattr(stmt, "col_offset", 0),
                )
            )
            continue
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
            and tree.body[0] is stmt
        ):
            continue  # module docstring
        diagnostics.append(
            _diagnostic(
                "module_level_statement",
                "reject",
                "module-level executable statements other than the single feature "
                "function (and docstring) are rejected",
                getattr(stmt, "lineno", 0),
                getattr(stmt, "col_offset", 0),
            )
        )

    annotation_names = _check_bindings_and_context(tree, funcs, diagnostics)
    local_names: set = set()
    for func in funcs:
        if func.decorator_list:
            diagnostics.append(
                _diagnostic(
                    "disallowed_decorator",
                    "reject",
                    "decorators are rejected in v1",
                    getattr(func, "lineno", 0),
                    getattr(func, "col_offset", 0),
                )
            )
        a = func.args
        if a.vararg is not None or a.kwarg is not None or a.kwonlyargs:
            diagnostics.append(
                _diagnostic(
                    "disallowed_signature",
                    "reject",
                    "*args/**kwargs/keyword-only parameters are rejected in v1",
                    getattr(func, "lineno", 0),
                    getattr(func, "col_offset", 0),
                )
            )
        for default in list(a.defaults) + list(a.kw_defaults):
            if default is not None and not (
                isinstance(default, ast.Constant) and isinstance(default.value, (int, float, bool))
            ):
                diagnostics.append(
                    _diagnostic(
                        "disallowed_default",
                        "reject",
                        "only numeric/bool constant defaults are allowed",
                        getattr(default, "lineno", 0),
                        getattr(default, "col_offset", 0),
                    )
                )
        local_names |= _collect_locals(func)

    for node, _depth in _iter_stack(tree):
        name = type(node).__name__
        if name not in _ALLOWED_NODES:
            if isinstance(node, ast.Attribute):
                diagnostics.append(
                    _diagnostic(
                        "disallowed_attribute",
                        "reject",
                        "attribute access is outside the v1 arithmetic/input interface",
                        getattr(node, "lineno", 0),
                        getattr(node, "col_offset", 0),
                    )
                )
            else:
                diagnostics.append(
                    _diagnostic(
                        "disallowed_node",
                        "reject",
                        "node type %s is not part of the v1 approved morphology" % name,
                        getattr(node, "lineno", 0),
                        getattr(node, "col_offset", 0),
                    )
                )
            continue
        _check_index_policy(node, diagnostics)

        if isinstance(node, ast.Constant):
            value = node.value
            if isinstance(value, float) and not math.isfinite(value):
                diagnostics.append(_diagnostic("nonfinite_literal", "reject",
                                               "non-finite float literals are rejected",
                                               node.lineno, node.col_offset))
            if isinstance(value, bool) or value is None or isinstance(value, (int, float, str)):
                if isinstance(value, int) and not isinstance(value, bool):
                    if value.bit_length() > MAX_INT_BITS:
                        diagnostics.append(
                            _diagnostic(
                                "oversized_literal",
                                "reject",
                                "integer literal exceeds fixed magnitude ceiling",
                                getattr(node, "lineno", 0),
                                getattr(node, "col_offset", 0),
                            )
                        )
            else:
                diagnostics.append(
                    _diagnostic(
                        "disallowed_literal",
                        "reject",
                        "literal type %s is rejected in v1" % type(value).__name__,
                        getattr(node, "lineno", 0),
                        getattr(node, "col_offset", 0),
                    )
                )
        elif isinstance(node, ast.Name):
            if id(node) in annotation_names:
                continue
            if isinstance(node.ctx, ast.Load):
                if node.id in FORBIDDEN_NAMES:
                    diagnostics.append(
                        _diagnostic(
                            "forbidden_name",
                            "reject",
                            "name %s is forbidden" % node.id,
                            getattr(node, "lineno", 0),
                            getattr(node, "col_offset", 0),
                        )
                    )
                elif node.id not in local_names and node.id not in CALL_WHITELIST:
                    diagnostics.append(
                        _diagnostic(
                            "unknown_name",
                            "reject",
                            "name %s is neither a local nor a whitelisted builtin" % node.id,
                            getattr(node, "lineno", 0),
                            getattr(node, "col_offset", 0),
                        )
                    )
            else:
                if node.id in FORBIDDEN_NAMES:
                    diagnostics.append(
                        _diagnostic(
                            "forbidden_name",
                            "reject",
                            "assignment to %s is forbidden" % node.id,
                            getattr(node, "lineno", 0),
                            getattr(node, "col_offset", 0),
                        )
                    )
        elif isinstance(node, ast.Call):
            func_expr = node.func
            if not (
                isinstance(func_expr, ast.Name)
                and func_expr.id in CALL_WHITELIST
                and isinstance(func_expr.ctx, ast.Load)
            ):
                diagnostics.append(
                    _diagnostic(
                        "dynamic_call",
                        "reject",
                        "only direct calls of whitelisted builtins are allowed",
                        getattr(node, "lineno", 0),
                        getattr(node, "col_offset", 0),
                    )
                )
            if node.keywords:
                diagnostics.append(
                    _diagnostic(
                        "disallowed_keyword_argument",
                        "reject",
                        "keyword arguments are rejected in v1",
                        getattr(node, "lineno", 0),
                        getattr(node, "col_offset", 0),
                    )
                )
            if len(node.args) > MAX_CALL_ARGS:
                diagnostics.append(
                    _diagnostic(
                        "call_arity_limit",
                        "reject",
                        "call arity exceeds fixed ceiling",
                        getattr(node, "lineno", 0),
                        getattr(node, "col_offset", 0),
                    )
                )
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    diagnostics.append(
                        _diagnostic(
                            "disallowed_target",
                            "reject",
                            "assignment targets must be plain local names",
                            getattr(target, "lineno", 0),
                            getattr(target, "col_offset", 0),
                        )
                    )
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            if not isinstance(node.target, ast.Name):
                diagnostics.append(
                    _diagnostic(
                        "disallowed_target",
                        "reject",
                        "assignment targets must be plain local names",
                        getattr(node.target, "lineno", 0),
                        getattr(node.target, "col_offset", 0),
                    )
                )
            if isinstance(node, ast.AnnAssign) and not (
                isinstance(node.annotation, ast.Name) and node.annotation.id in ALLOWED_ANNOTATIONS
            ):
                diagnostics.append(
                    _diagnostic(
                        "disallowed_annotation",
                        "reject",
                        "annotations are restricted to a fixed set of builtin names",
                        getattr(node, "lineno", 0),
                        getattr(node, "col_offset", 0),
                    )
                )
        elif isinstance(node, ast.For):
            if not (
                isinstance(node.iter, ast.Name)
                or (
                    isinstance(node.iter, ast.Call)
                    and isinstance(node.iter.func, ast.Name)
                    and node.iter.func.id == "range"
                )
            ):
                diagnostics.append(
                    _diagnostic(
                        "disallowed_iteration_source",
                        "reject",
                        "for-loops must iterate range(...) or a plain input name",
                        getattr(node, "lineno", 0),
                        getattr(node, "col_offset", 0),
                    )
                )
        elif isinstance(node, ast.Expr):
            value = node.value
            if not (
                isinstance(value, ast.Call)
                or isinstance(value, ast.Constant)
                or isinstance(value, ast.Name)
            ):
                diagnostics.append(
                    _diagnostic(
                        "bare_expression_statement",
                        "reject",
                        "bare expression statements are limited to inert calls, names "
                        "and constants in v1",
                        getattr(node, "lineno", 0),
                        getattr(node, "col_offset", 0),
                    )
                )


def _check_source(source: bytes) -> dict:
    """Run the dormant structural first pass over candidate source bytes.

    Pure and side-effect free: never compiles, imports, evaluates or
    materialises anything from ``source``; ``ast.parse`` is used for syntax
    inspection only.  The returned report always carries
    ``authority_granted=False``, ``execution_enabled=False`` and
    ``boundary_required=True``.  Dispositions: ``accept_morphology``,
    ``reject`` (candidate-side morphology violation) or ``refuse``
    (deterministic resource/trust refusal; not a repairable candidate fault).
    """
    diagnostics: list = []
    report = _empty_report(0)

    if type(source) is not bytes:
        diagnostics.append(
            _diagnostic(
                "invalid_input_type",
                "refuse",
                "check_source requires bytes; no implicit conversion is performed",
            )
        )
        return _finalise(report, diagnostics)

    report["checked_bytes"] = len(source)

    # 1. Size ceiling BEFORE any decode or parse.
    if len(source) > MAX_SOURCE_BYTES:
        diagnostics.append(
            _diagnostic(
                "source_size_limit",
                "refuse",
                "source exceeds the fixed %d byte ceiling; not decoded or parsed"
                % MAX_SOURCE_BYTES,
            )
        )
        return _finalise(report, diagnostics)

    # 2. Strict UTF-8 decode.
    try:
        text = source.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        diagnostics.append(
            _diagnostic("invalid_utf8", "reject", "source is not valid UTF-8 and is rejected")
        )
        return _finalise(report, diagnostics)

    # 3. Conservative preparse bounds (tokenize; outside strings).
    bounds_ok, tokenize_failed = _preparse_bounds(text, diagnostics)
    if not bounds_ok:
        return _finalise(report, diagnostics)

    # 4. Syntax inspection only. Parser failures become deterministic refusals.
    try:
        tree = ast.parse(text, mode="exec")
    except SyntaxError as exc:
        diagnostics.append(
            _diagnostic(
                "syntax_error",
                "reject",
                "source does not parse: %s" % (exc.msg or "syntax error"),
                getattr(exc, "lineno", 0) or 0,
                getattr(exc, "offset", 0) or 0,
            )
        )
        return _finalise(report, diagnostics)
    except (RecursionError, MemoryError, ValueError, OverflowError, IndexError):
        diagnostics.append(
            _diagnostic(
                "parser_failure",
                "refuse",
                "parser refused the input deterministically (resource or "
                "representation limit); no repair is attempted",
            )
        )
        return _finalise(report, diagnostics)
    if tokenize_failed:
        diagnostics.append(
            _diagnostic(
                "preparse_unverified",
                "refuse",
                "preparse tokenizer could not verify resource bounds; refusing "
                "conservatively even though the syntax parses",
            )
        )
        return _finalise(report, diagnostics)

    # 5. Iterative AST walk with fixed node/depth ceilings.
    node_count = 0
    max_depth = 0
    limit_hit = False
    for _node, depth in _iter_stack(tree):
        node_count += 1
        if node_count > MAX_AST_NODES:
            diagnostics.append(
                _diagnostic(
                    "ast_node_limit",
                    "refuse",
                    "AST node count exceeds fixed ceiling; walk aborted",
                )
            )
            limit_hit = True
            break
        if depth > max_depth:
            max_depth = depth
        if depth > MAX_AST_DEPTH:
            diagnostics.append(
                _diagnostic(
                    "ast_depth_limit",
                    "refuse",
                    "AST depth exceeds fixed ceiling; walk aborted",
                )
            )
            limit_hit = True
            break
    if limit_hit:
        return _finalise(report, diagnostics)

    # 6. Approved morphology and conservative index syntax policy.
    _check_semantics(tree, diagnostics)

    return _finalise(report, diagnostics)


def check_source(source: bytes) -> dict:
    """Inspect bytes only; never execute them or grant runtime authority.

    Normalize observed resource failures throughout decoding, tokenizing and
    AST inspection. External process containment remains mandatory: reporting
    itself needs memory and cannot survive every exhausted/killed process.
    """
    try:
        return _check_source(source)
    except (RecursionError, MemoryError, ValueError, OverflowError, IndexError):
        report = _empty_report(len(source) if type(source) is bytes else 0)
        return _finalise(report, [_diagnostic(
            "inspection_failure", "refuse",
            "inspection could not complete within resource or representation limits")])
