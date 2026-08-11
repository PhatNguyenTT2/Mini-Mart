from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from ai_service.errors import ArtifactIntegrityError
from ai_service.export.bundle import BundlePublisher, file_sha256, verify_bundle
from tests.support.v5_factories import make_full_stat_rule_store, make_settings, make_snapshot


def _build_bundle(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    settings = make_settings(tmp_path)
    snapshot = make_snapshot(tmp_path)
    ranker = tmp_path / "ranker.onnx"
    ranker.write_bytes(b"fixture-onnx")
    dim = settings.model.item_emb_dim
    parity = SimpleNamespace(
        max_abs_error=0.0,
        ranking_parity_users=4,
        kernel_latency_ms={"p50": 0.1, "p95": 0.2},
        hardware={"device": "cpu"},
    )
    bundle = BundlePublisher(settings).publish(
        bundle_id="bundle-edge",
        run_id="hybrid-edge",
        snapshot=snapshot,
        rule_store=make_full_stat_rule_store(snapshot.manifest.num_items),
        ranker_path=ranker,
        item_vectors=np.zeros((snapshot.manifest.num_items, dim), dtype=np.float32),
        user_profile_vectors=np.zeros((snapshot.manifest.num_users + 1, dim), dtype=np.float32),
        embedding_sha256="b" * 64,
        rule_sha256="c" * 64,
        checkpoint_sha256="d" * 64,
        comparison_signature_sha256=settings.comparison_signature_sha256(),
        parity=parity,
        victory_matrix_sha256="e" * 64,
    )
    return bundle.path


def _publish_direct(
    tmp_path: Path,
    *,
    bundle_id: str = "bundle-direct",
    item_vectors: np.ndarray | None = None,
    user_profiles: np.ndarray | None = None,
    victory_matrix_sha256: str = "e" * 64,
) -> Path:
    settings = make_settings(tmp_path)
    snapshot = make_snapshot(tmp_path)
    ranker = tmp_path / "ranker-direct.onnx"
    ranker.write_bytes(b"fixture-onnx")
    dim = settings.model.item_emb_dim
    artifact = BundlePublisher(settings).publish(
        bundle_id=bundle_id,
        run_id="hybrid-direct",
        snapshot=snapshot,
        rule_store=make_full_stat_rule_store(snapshot.manifest.num_items),
        ranker_path=ranker,
        item_vectors=item_vectors
        if item_vectors is not None
        else np.zeros((snapshot.manifest.num_items, dim), dtype=np.float32),
        user_profile_vectors=user_profiles
        if user_profiles is not None
        else np.zeros((snapshot.manifest.num_users + 1, dim), dtype=np.float32),
        embedding_sha256="b" * 64,
        rule_sha256="c" * 64,
        checkpoint_sha256="d" * 64,
        comparison_signature_sha256=settings.comparison_signature_sha256(),
        parity=SimpleNamespace(
            max_abs_error=0.0,
            ranking_parity_users=4,
            kernel_latency_ms={"p50": 0.1, "p95": 0.2},
            hardware={"device": "cpu"},
        ),
        victory_matrix_sha256=victory_matrix_sha256,
    )
    return artifact.path


def _refresh_file_hashes(bundle: Path) -> None:
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = {name: file_sha256(bundle / name) for name in manifest["files"]}
    manifest["content_sha256"] = hashlib.sha256(
        "\n".join(
            f"{name}\t{checksum}" for name, checksum in sorted(manifest["files"].items())
        ).encode()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_bundle_verifier_rejects_directory_and_parent_lineage_edges(tmp_path: Path) -> None:
    bundle = _build_bundle(tmp_path)
    (bundle / "unexpected.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="unexpected files"):
        verify_bundle(bundle)
    (bundle / "unexpected.txt").unlink()
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["parent_sha256"]["victory_matrix"] = "f" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="victory matrix lineage"):
        verify_bundle(bundle)


@pytest.mark.parametrize("mutation", ["item", "profile", "mapping", "rules", "q99", "csr"])
def test_bundle_verifier_rejects_numerical_and_mapping_edges(tmp_path: Path, mutation: str) -> None:
    bundle = _build_bundle(tmp_path)
    if mutation == "item":
        np.save(bundle / "item_vectors.npy", np.zeros((1, 1), dtype=np.float64))
    elif mutation == "profile":
        np.save(bundle / "user_profile_vectors.npy", np.zeros((1, 1), dtype=np.float32))
    elif mutation == "mapping":
        mappings = json.loads((bundle / "mappings.json").read_text(encoding="utf-8"))
        mappings["product_map"] = {"bad": 0}
        (bundle / "mappings.json").write_text(json.dumps(mappings), encoding="utf-8")
    else:
        with np.load(bundle / "rules.npz", allow_pickle=False) as archive:
            arrays = {name: archive[name] for name in archive.files}
        if mutation == "rules":
            arrays.pop("features")
        elif mutation == "q99":
            arrays["q99_log_lift"] = np.asarray([0.0], dtype=np.float32)
        else:
            arrays["crow_indices"] = arrays["crow_indices"].copy()
            arrays["crow_indices"][-1] += 1
        np.savez_compressed(bundle / "rules.npz", **arrays)
    _refresh_file_hashes(bundle)
    expected = {
        "item": "item vector",
        "profile": "user profile",
        "mapping": "product mapping",
        "rules": "rule cache",
        "q99": "rule arrays",
        "csr": "CSR bounds",
    }[mutation]
    with pytest.raises(ArtifactIntegrityError, match=expected):
        verify_bundle(bundle)


def test_bundle_verifier_rejects_invalid_config_signature_and_parity(tmp_path: Path) -> None:
    bundle = _build_bundle(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["parity_max_abs"] = 0.1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="parity"):
        verify_bundle(bundle)

    bundle = _build_bundle(tmp_path / "second")
    resolved_path = bundle / "resolved-config.json"
    resolved = json.loads(resolved_path.read_text(encoding="utf-8"))
    resolved["schema_version"] = "4.0.0"
    resolved_path.write_text(json.dumps(resolved), encoding="utf-8")
    _refresh_file_hashes(bundle)
    with pytest.raises(ArtifactIntegrityError, match="configuration schema"):
        verify_bundle(bundle)


def test_bundle_publish_verifies_temporary_before_immutable_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = make_settings(tmp_path)
    snapshot = make_snapshot(tmp_path)
    ranker = tmp_path / "ranker.onnx"
    ranker.write_bytes(b"fixture-onnx")
    original_verify = verify_bundle

    def fail_for_temporary(path: Path) -> object:
        if path.name.startswith(".bundle-preflight-"):
            raise ArtifactIntegrityError("injected temporary verification failure")
        return original_verify(path)

    monkeypatch.setattr("ai_service.export.bundle.verify_bundle", fail_for_temporary)
    with pytest.raises(ArtifactIntegrityError, match="temporary verification"):
        BundlePublisher(settings).publish(
            bundle_id="bundle-preflight",
            run_id="hybrid-preflight",
            snapshot=snapshot,
            rule_store=make_full_stat_rule_store(snapshot.manifest.num_items),
            ranker_path=ranker,
            item_vectors=np.zeros(
                (snapshot.manifest.num_items, settings.model.item_emb_dim), dtype=np.float32
            ),
            user_profile_vectors=np.zeros(
                (snapshot.manifest.num_users + 1, settings.model.item_emb_dim), dtype=np.float32
            ),
            embedding_sha256="b" * 64,
            rule_sha256="c" * 64,
            checkpoint_sha256="d" * 64,
            comparison_signature_sha256=settings.comparison_signature_sha256(),
            parity=SimpleNamespace(
                max_abs_error=0.0,
                ranking_parity_users=4,
                kernel_latency_ms={"p50": 0.1, "p95": 0.2},
                hardware={"device": "cpu"},
            ),
            victory_matrix_sha256="e" * 64,
        )
    assert not (settings.data.artifact_root / "bundles" / "bundle-preflight").exists()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("hash", "non-placeholder"),
        ("item", "item vector"),
        ("profile", "user profile"),
        ("row0", "unknown-user"),
    ],
)
def test_bundle_publish_rejects_invalid_inputs_before_destination(
    tmp_path: Path, mutation: str, message: str
) -> None:
    settings = make_settings(tmp_path)
    snapshot = make_snapshot(tmp_path)
    dim = settings.model.item_emb_dim
    kwargs: dict[str, object] = {}
    if mutation == "hash":
        kwargs["victory_matrix_sha256"] = "0" * 64
    elif mutation == "item":
        kwargs["item_vectors"] = np.zeros((1, 1), dtype=np.float32)
    elif mutation == "profile":
        kwargs["user_profiles"] = np.zeros((1, 1), dtype=np.float32)
    else:
        profiles = np.zeros((snapshot.manifest.num_users + 1, dim), dtype=np.float32)
        profiles[0, 0] = 1.0
        kwargs["user_profiles"] = profiles
    with pytest.raises(ArtifactIntegrityError, match=message):
        _publish_direct(tmp_path, bundle_id=f"bundle-{mutation}", **kwargs)  # type: ignore[arg-type]
    assert not (settings.data.artifact_root / "bundles" / f"bundle-{mutation}").exists()


def test_bundle_publish_rejects_existing_destination(tmp_path: Path) -> None:
    bundle = _build_bundle(tmp_path)
    settings = make_settings(tmp_path)
    snapshot = make_snapshot(tmp_path)
    ranker = tmp_path / "ranker-existing.onnx"
    ranker.write_bytes(b"fixture-onnx")
    with pytest.raises(ArtifactIntegrityError, match="already exists"):
        BundlePublisher(settings).publish(
            bundle_id=bundle.name,
            run_id="hybrid-existing",
            snapshot=snapshot,
            rule_store=make_full_stat_rule_store(snapshot.manifest.num_items),
            ranker_path=ranker,
            item_vectors=np.zeros(
                (snapshot.manifest.num_items, settings.model.item_emb_dim), dtype=np.float32
            ),
            user_profile_vectors=np.zeros(
                (snapshot.manifest.num_users + 1, settings.model.item_emb_dim), dtype=np.float32
            ),
            embedding_sha256="b" * 64,
            rule_sha256="c" * 64,
            checkpoint_sha256="d" * 64,
            comparison_signature_sha256=settings.comparison_signature_sha256(),
            parity=SimpleNamespace(
                max_abs_error=0.0,
                ranking_parity_users=4,
                kernel_latency_ms={"p50": 0.1, "p95": 0.2},
                hardware={"device": "cpu"},
            ),
            victory_matrix_sha256="e" * 64,
        )


def test_bundle_manifest_parse_and_rules_load_errors_are_wrapped(tmp_path: Path) -> None:
    bundle = _build_bundle(tmp_path)
    (bundle / "manifest.json").write_text("{", encoding="utf-8")
    with pytest.raises(ArtifactIntegrityError, match="manifest cannot be read"):
        verify_bundle(bundle)

    bundle = _build_bundle(tmp_path / "rules")
    (bundle / "rules.npz").write_bytes(b"not-an-npz")
    _refresh_file_hashes(bundle)
    with pytest.raises(ArtifactIntegrityError, match="rule cache cannot be loaded"):
        verify_bundle(bundle)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("manifest-files", "exact file allowlist"),
        ("missing-file", "bundle file missing"),
        ("checksum", "checksum mismatch"),
        ("aggregate", "aggregate checksum"),
        ("placeholder", "placeholder"),
        ("lineage-set", "lineage is incomplete"),
        ("lineage-sha", "invalid SHA"),
        ("signature-read", "training signature cannot be read"),
        ("signature-format", "training signature is invalid"),
        ("config-parse", "resolved configuration is invalid"),
        ("config-variant", "resolved configuration is not Hybrid"),
        ("training-signature", "training signature does not match"),
        ("comparison-signature", "comparison signature does not match"),
        ("numeric-load", "numerical artifacts cannot be loaded"),
        ("mapping-object", "mappings must be an object"),
        ("product-value", "product mapping does not match"),
        ("user-value", "user profile cache has invalid shape"),
        ("csr-length", "CSR row pointer length"),
    ],
)
def test_bundle_verifier_rejects_manifest_and_loader_corruption(
    tmp_path: Path, mutation: str, message: str
) -> None:
    bundle = _build_bundle(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if mutation == "manifest-files":
        manifest["files"].pop("ranker.onnx")
    elif mutation == "missing-file":
        (bundle / "ranker.onnx").unlink()
        (bundle / "ranker.onnx").mkdir()
    elif mutation == "checksum":
        (bundle / "ranker.onnx").write_bytes(b"mutated")
    elif mutation == "aggregate":
        manifest["content_sha256"] = "f" * 64
    elif mutation == "placeholder":
        manifest["victory_matrix_sha256"] = "0" * 64
    elif mutation == "lineage-set":
        manifest["parent_sha256"].pop("rules")
    elif mutation == "lineage-sha":
        manifest["parent_sha256"]["rules"] = "not-a-sha"
    elif mutation == "signature-read":
        (bundle / "training-signature.sha256").write_bytes(b"\xff")
    elif mutation == "signature-format":
        (bundle / "training-signature.sha256").write_text("bad", encoding="ascii")
    elif mutation == "config-parse":
        (bundle / "resolved-config.json").write_text("{", encoding="utf-8")
    elif mutation == "config-variant":
        resolved = json.loads((bundle / "resolved-config.json").read_text(encoding="utf-8"))
        resolved["train"]["training_variant"] = "deep_only"
        (bundle / "resolved-config.json").write_text(json.dumps(resolved), encoding="utf-8")
    elif mutation == "training-signature":
        (bundle / "training-signature.sha256").write_text("f" * 64, encoding="ascii")
    elif mutation == "comparison-signature":
        manifest["comparison_signature_sha256"] = "f" * 64
    elif mutation == "numeric-load":
        (bundle / "item_vectors.npy").write_bytes(b"bad-npy")
    elif mutation == "mapping-object":
        (bundle / "mappings.json").write_text("[]", encoding="utf-8")
    elif mutation == "product-value":
        mappings = json.loads((bundle / "mappings.json").read_text(encoding="utf-8"))
        mappings["product_map"] = {"bad": "x"}
        (bundle / "mappings.json").write_text(json.dumps(mappings), encoding="utf-8")
    elif mutation == "user-value":
        mappings = json.loads((bundle / "mappings.json").read_text(encoding="utf-8"))
        mappings["user_map"] = {"bad": "x"}
        (bundle / "mappings.json").write_text(json.dumps(mappings), encoding="utf-8")
    else:
        with np.load(bundle / "rules.npz", allow_pickle=False) as archive:
            arrays = {name: archive[name] for name in archive.files}
        arrays["crow_indices"] = arrays["crow_indices"][:-1]
        np.savez_compressed(bundle / "rules.npz", **arrays)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    if mutation not in {
        "manifest-files",
        "missing-file",
        "checksum",
        "placeholder",
        "aggregate",
        "lineage-set",
        "lineage-sha",
        "comparison-signature",
    }:
        _refresh_file_hashes(bundle)
    with pytest.raises(ArtifactIntegrityError, match=message):
        verify_bundle(bundle)


def test_bundle_publish_rechecks_race_before_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = make_settings(tmp_path)
    ranker = tmp_path / "ranker-race.onnx"
    ranker.write_bytes(b"fixture-onnx")
    original_verify = verify_bundle
    destination = settings.data.artifact_root / "bundles" / "bundle-race"

    def race_verify(path: Path) -> object:
        result = original_verify(path)
        if path.name.startswith(".bundle-race-"):
            destination.mkdir(parents=True)
        return result

    monkeypatch.setattr("ai_service.export.bundle.verify_bundle", race_verify)
    with pytest.raises(ArtifactIntegrityError, match="already exists"):
        _publish_direct(tmp_path, bundle_id="bundle-race")
