"""Back-compat shim: the real package is ``eco_harness.backend``.

See ``agent/__init__.py`` for the rationale. ``backend.server`` and other
historical ``backend.*`` imports keep working inside a source checkout; the
installed wheel ships only ``eco_harness.*``. Submodules are aliased (not
re-imported) so both spellings share module state and class identity.
"""
import importlib
import pkgutil
import sys as _sys

import eco_harness.backend as _backend


def _alias(prefix: str, package) -> None:
    _sys.modules[prefix] = package
    stack: list[tuple[str, object]] = [(prefix, package)]
    while stack:
        legacy_name, pkg = stack.pop()
        for info in pkgutil.iter_modules(getattr(pkg, "__path__", [])):
            child_legacy = f"{legacy_name}.{info.name}"
            try:
                module = importlib.import_module(
                    f"eco_harness.{child_legacy}",
                )
            except Exception:  # noqa: BLE001 - shim must never break the app
                continue
            _sys.modules.setdefault(child_legacy, module)
            if info.ispkg:
                stack.append((child_legacy, module))


_alias(__name__, _backend)
