"""Contrato dinámico: cubre también los módulos añadidos después del ejemplo."""

from __future__ import annotations

from grimp import ImportGraph
from importlinter import Contract, ContractCheck, output


class BoundedContextsContract(Contract):
    def check(self, graph: ImportGraph, verbose: bool) -> ContractCheck:
        violations: list[str] = []
        for importer in sorted(graph.modules):
            source = importer.split(".")
            if len(source) < 2 or source[0] != "applications":
                continue
            for imported in sorted(graph.find_modules_directly_imported_by(importer)):
                target = imported.split(".")
                if len(target) < 2 or target[0] != "applications":
                    continue
                cross_context = source[1] != target[1]
                public_target = len(target) > 2 and target[2] in {"services", "public"}
                data_importer = len(source) > 2 and source[2] in {"models", "managers"}
                public_reexport = len(source) > 2 and source[2] == "public" and (
                    len(target) < 3 or target[2] not in {"services", "selectors", "public"}
                )
                if (cross_context and (not public_target or data_importer)) or public_reexport:
                    violations.append(f"{importer} -> {imported}")
        return ContractCheck(kept=not violations, metadata={"violations": violations})

    def render_broken_contract(self, check: ContractCheck) -> None:
        for violation in check.metadata["violations"]:
            output.print_error(violation, bold=False)
