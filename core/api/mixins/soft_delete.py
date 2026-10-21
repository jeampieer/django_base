from typing import Any


class SoftDeleteViewMixin:
    """Adaptación del mixin original para modelos que heredan de BaseModel."""

    def perform_soft_delete(self, instance: Any, user: Any = None) -> None:
        instance.soft_delete(user=user)

    def perform_restore(self, instance: Any, user: Any = None) -> None:
        instance.restore(user=user)
