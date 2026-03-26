"""
Состояния процесса распознавания объекта (паттерн State).
idle: ожидание наведения на объект.
step1: снятие подписи и определение по базе.
"""


class RecognitionState:
    """Базовый класс состояния распознавания."""

    @property
    def is_idle(self) -> bool:
        return False

    @property
    def is_step1(self) -> bool:
        return False


class RecognitionIdle(RecognitionState):
    """Ожидание наведения на объект."""

    @property
    def is_idle(self) -> bool:
        return True


class RecognitionStep1(RecognitionState):
    """Снятие подписи и определение по базе."""

    @property
    def is_step1(self) -> bool:
        return True
