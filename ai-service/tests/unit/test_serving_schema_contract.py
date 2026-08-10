import pytest
from pydantic import ValidationError

from ai_service.serving.schemas import RecommendRequest


def test_recommend_request_requires_store_and_unique_bounded_candidates() -> None:
    with pytest.raises(ValidationError):
        RecommendRequest(candidate_product_ids=[1001])
    with pytest.raises(ValidationError):
        RecommendRequest(store_id=1, candidate_product_ids=[1001, 1001])
    request = RecommendRequest(
        store_id=1,
        user_id=None,
        persona_cluster=None,
        candidate_product_ids=[1001, 1002],
        context_product_id=None,
    )
    assert request.store_id == 1
    assert request.candidate_product_ids == [1001, 1002]
