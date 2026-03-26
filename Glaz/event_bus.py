"""
Шина событий (паттерн Observer): подписка на события и уведомление подписчиков.
"""

from typing import Any, Callable


class EventBus:
    """Шина событий: имена событий и списки подписчиков."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable[..., None]]] = {}

    def subscribe(self, event: str, callback: Callable[..., None]) -> None:
        """Подписаться на событие."""
        if event not in self._subscribers:
            self._subscribers[event] = []
        self._subscribers[event].append(callback)

    def emit(self, event: str, **payload: Any) -> None:
        """Оповестить подписчиков о событии."""
        for cb in self._subscribers.get(event, []):
            try:
                cb(**payload)
            except Exception:
                pass  # не ломаем поток при ошибке в подписчике
