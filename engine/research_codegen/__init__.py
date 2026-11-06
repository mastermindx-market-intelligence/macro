"""Inert research-codegen contract validation package.

Importing this package performs no work: it loads no sibling modules, starts
no runtime, and performs no I/O.  The validators live in the explicit
submodules ``contracts``, ``input_contract``, ``output_contract`` and
``admission`` and must be imported directly.  This initializer deliberately
does not import, re-export, wrap or shadow the existing ``accounting_contract``,
``evaluation`` or ``transport`` modules, and it binds none of their names.
Every exported validator returns structural violation lists or fixed dormant
assessment dictionaries only; none can enable generation, execution,
evaluation or authority.
"""

__all__: list = []
