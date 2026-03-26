"""Registry/repository integration for object signatures."""

from __future__ import annotations

from dataclasses import dataclass

from Glaz.objects_repository import ObjectsRepository


@dataclass(frozen=True)
class RecognitionResult:
    """Recognition output."""

    refined_id: int
    is_new: bool


class ObjectRegistry:
    """Stores and matches detected object signatures."""

    def __init__(self) -> None:
        self._repo = ObjectsRepository()
        self._full_signature_to_ids, self._zoomed_signature_to_ids, self._next_refined_id = self._repo.load()

    def recognize(self, signature: tuple[int, ...], max_diff_pct: float = 0.2) -> RecognitionResult:
        """Find known object by signature or register a new one."""
        match = self._repo.find_similar(signature, self._zoomed_signature_to_ids, max_diff_pct=max_diff_pct)
        if match:
            known_sig, _ = match
            return RecognitionResult(refined_id=self._zoomed_signature_to_ids[known_sig][0], is_new=False)

        refined_id = self._next_refined_id
        self._next_refined_id += 1
        self._zoomed_signature_to_ids.setdefault(signature, []).append(refined_id)
        self._repo.save(
            self._full_signature_to_ids,
            self._zoomed_signature_to_ids,
            self._next_refined_id,
        )
        return RecognitionResult(refined_id=refined_id, is_new=True)

