from typing import Any

from core.auth.policy import BasePolicy


class PolicyRegistry:
    def __init__(self) -> None:
        self._policies: dict[str, type[BasePolicy]] = {}

    def register(self, policy_class: type[BasePolicy]) -> None:
        label = getattr(policy_class, "model_label", None)
        if not label:
            raise ValueError(f"{policy_class.__name__} debe definir model_label.")
        self._policies[label] = policy_class

    def get(self, role: str, model_label: str, *, superuser: bool = False) -> dict[str, Any]:
        policy = self._policies.get(model_label)
        return policy.to_role_dict(role, superuser=superuser) if policy else {}

    def all_policies(self) -> dict[str, type[BasePolicy]]:
        return dict(self._policies)

    def registered_labels(self) -> list[str]:
        return list(self._policies)


policy_registry = PolicyRegistry()
