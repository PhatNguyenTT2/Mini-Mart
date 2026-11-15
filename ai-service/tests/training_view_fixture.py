"""Minimal Instacart-shaped training view shared by pair-rule tests."""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np

from ai_service_v2.adapters.instacart import InstacartTrainingBasket, TrainPairBatch


class FixtureTrainingView:
    manifest_sha256 = "a" * 64
    raw_user_ids = (10, 20, 30)
    raw_item_ids = (2, 4, 7, 9)

    @property
    def test_access_state(self) -> str:
        return "LOCKED_NOT_ACCESSED"

    def iter_train_pairs(self, *, batch_size: int = 262_144) -> Iterator[TrainPairBatch]:
        del batch_size
        yield TrainPairBatch(
            user_ids=np.asarray([0, 0, 0, 0, 1, 2], dtype=np.int32),
            item_ids=np.asarray([0, 1, 2, 3, 2, 3], dtype=np.int32),
        )

    def iter_train_baskets(self) -> Iterator[InstacartTrainingBasket]:
        yield InstacartTrainingBasket(0, 2, 102, (1, 3))
        yield InstacartTrainingBasket(1, 1, 201, (2,))
        yield InstacartTrainingBasket(0, 1, 101, (0, 2))
        yield InstacartTrainingBasket(2, 1, 301, (3,))
