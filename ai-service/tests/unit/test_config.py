"""Unit tests for config.py settings and path resolutions."""

import os
from pathlib import Path
import pytest
from config import get_settings, set_seed, BASE_DIR, ModelConfig


def test_get_settings_defaults():
    settings = get_settings()
    assert settings.data.store_id == 1
    assert settings.data.num_users == 5000
    assert settings.data.num_items == 5200
    assert settings.data.num_personas == 8
    assert settings.data.num_leaf_categories == 40
    assert settings.data.num_price_buckets == 8

    assert settings.model.user_emb_dim == 64
    assert settings.model.persona_emb_dim == 8
    assert settings.model.category_emb_dim == 16
    assert settings.model.price_emb_dim == 8
    assert settings.model.sbert_dim == 768
    assert settings.model.item_emb_dim == 64
    assert settings.model.tau == 0.1

    assert settings.train.batch_size == 2048
    assert settings.train.negative_ratio == 4
    assert settings.train.lr == 1e-3
    assert settings.train.seed == 42


def test_invalid_tau():
    with pytest.raises(ValueError, match="Temperature tau must be strictly positive"):
        ModelConfig(tau=0.0)

    with pytest.raises(ValueError, match="Temperature tau must be strictly positive"):
        ModelConfig(tau=-0.1)


def test_base_dir_resolution():
    assert BASE_DIR.name == "ai-service"
    assert (BASE_DIR / "config.py").exists()


def test_set_seed():
    set_seed(123)
    assert os.environ.get("PYTHONHASHSEED") == "123"
