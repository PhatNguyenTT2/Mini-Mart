from __future__ import annotations

from pathlib import Path

import pytest

from ai_service.config import DataConfig, ModelConfig, Settings, load_settings
from ai_service.errors import ConfigurationError


def test_model_temperature_and_data_split_configuration_fail_closed() -> None:
    with pytest.raises(ValueError, match="tau"):
        ModelConfig(tau=0.0001)
    with pytest.raises(ValueError, match="split counts"):
        DataConfig(expected_event_count=10)


def test_production_requires_explicit_paths_databases_and_ca(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "AI_ARTIFACT_ROOT",
        "AI_STORE_ID",
        "CHATBOT_DATABASE_URL",
        "CATALOG_DATABASE_URL",
        "ORDER_DATABASE_URL",
        "SUPABASE_DB_CA_PATH",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings()
    settings.serving.environment = "production"

    with pytest.raises(ConfigurationError, match="missing production settings"):
        settings.validate_production()


def test_toml_config_is_resolved_and_training_signature_ignores_machine_paths(
    tmp_path: Path,
) -> None:
    config = tmp_path / "training.toml"
    config.write_text(
        """
[model]
tau = 0.07

[train]
learning_rate = 0.0003
max_epochs = 30
explicit_negative_ratio = 16

[eval]
primary_metric = "gauc"
""".strip(),
        encoding="utf-8",
    )

    first = load_settings(config)
    second = load_settings(config)
    first.data.artifact_root = tmp_path / "machine-a"
    second.data.artifact_root = tmp_path / "machine-b"

    assert first.model.tau == 0.07
    assert first.train.learning_rate == 0.0003
    assert first.train.explicit_negative_ratio == 16
    assert first.eval.primary_metric == "gauc"
    assert first.training_signature_sha256() == second.training_signature_sha256()
    second.train.seed = 2027
    assert first.training_signature_sha256() != second.training_signature_sha256()
    assert first.experiment_signature_sha256() == second.experiment_signature_sha256()
    assert first.resolved_document()["train"]["max_epochs"] == 30


def test_all_locked_ablation_configs_are_valid_and_semantically_distinct() -> None:
    root = Path(__file__).parents[2] / "configs" / "ablations"
    settings = {path.stem: load_settings(path) for path in sorted(root.glob("*.toml"))}

    assert set(settings) == {"v3", "v4"}
    assert settings["v3"].train.training_variant == "deep_only"
    assert settings["v4"].train.training_variant == "hybrid"


def test_r3_feature_flags_change_model_signatures_and_configs_are_single_variable() -> None:
    baseline = Settings()
    no_user = Settings({"model": {"use_user_id_embedding": False}})
    no_price = Settings({"model": {"use_price_features": False}})
    assert baseline.training_signature_sha256() != no_user.training_signature_sha256()
    assert baseline.comparison_signature_sha256() != no_price.comparison_signature_sha256()

    root = Path(__file__).parents[2] / "configs" / "diagnostics" / "r3"
    configs = {path.stem: load_settings(path) for path in root.glob("*.toml")}
    assert set(configs) == {
        "deep-control",
        "deep-no-price",
        "deep-no-user-id",
        "deep-no-price-no-user-id",
        "hybrid-no-price",
        "hybrid-no-user-id",
        "hybrid-no-price-no-user-id",
    }
    assert configs["deep-control"].model.use_user_id_embedding
    assert configs["deep-control"].model.use_price_features
