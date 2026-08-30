from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


CREATED_AT = "2026-08-30T00:00:00+07:00"
STAGE_ID = "R6-C1R3-LINUX"
DOCKER_EXE = r"C:\Program Files\Docker\Docker\resources\bin\docker.exe"
DOCKER_EXE_BYTES = 42_748_848
DOCKER_EXE_SHA256 = "0cdb9dea2e39a0a29e5dc3f9732f572dc140547b28deab0495589b4f79b31ca1"
IMAGE_TAG = "docker.io/library/python:3.11.9-slim-bookworm"
IMAGE_INDEX_DIGEST = "sha256:8fb099199b9f2d70342674bd9dbccd3ed03a258f26bbd1d556822c6dfc60c317"
IMAGE_MANIFEST_DIGEST = "sha256:2856e6af199e8128161abd320575eb9b341f3b76f017b5d0c9cd364f60d8a050"
IMAGE_REF = f"docker.io/library/python@{IMAGE_MANIFEST_DIGEST}"
IMAGE_SOURCE_URL = (
    "https://hub.docker.com/layers/library/python/3.11.9-slim-bookworm/images/"
    "sha256-2856e6af199e8128161abd320575eb9b341f3b76f017b5d0c9cd364f60d8a050"
    "?context=explore"
)

DATA_ROOT = (
    r"E:\UIT\cv\materialized-data\hybrid-recsys-v5\stage1e\r6\official_source"
    r"\grouplens_ml100k\attempt-004-linux"
)
ENV_ROOT = (
    r"E:\UIT\cv\materialized-environments\hybrid-recsys-v5\stage1e\r6"
    r"\recbole_bpr_ml100k_py3119_cpu\attempt-004-linux"
)
SOURCE_ROOT = (
    r"E:\UIT\cv\backend\research\hybrid-recsys-v5\03_benchmark\stage1e"
    r"\materialized_sources\r5\recbole_v1_2_1_9a6f63d"
)
SOURCE_MANIFEST = (
    "research/hybrid-recsys-v5/03_benchmark/stage1e/rebaseline_v2/wave_ac/"
    "E4_R5M0_source_materialization/selected_blob_manifest.json"
)
G1_RECEIPT = (
    "research/hybrid-recsys-v5/03_benchmark/stage1e/00_control/"
    "rebaseline_v2_e4_r6_pc2w_g1_backend_admission_receipt.json"
)

RECBOLE_COMMIT = "9a6f63d8d4a5b989fe27955a833f813a6d86041e"
RECBOLE_TREE = "08915121fea069a30f7e3e97a72e16e7e76d43c6"
RECBOLE_MANIFEST_BYTES = 102_765
RECBOLE_MANIFEST_SHA256 = "c5794b9daccdd01ca600c6ef7f890918825fbbb872efa67036c4565234e87016"
RECBOLE_FILE_COUNT = 265
RECBOLE_TOTAL_BYTES = 1_541_044
RECBOLE_PY_FILE_COUNT = 150
RECBOLE_PY_TOTAL_BYTES = 1_378_341

ML100K_URL = "https://files.grouplens.org/datasets/movielens/ml-100k.zip"
ML100K_README_URL = "https://files.grouplens.org/datasets/movielens/ml-100k-README.txt"
ML100K_MD5_URL = "https://files.grouplens.org/datasets/movielens/ml-100k.zip.md5"
ML100K_BYTES = 4_924_029
ML100K_MD5 = "0e33842e24a9c977be4e0107933c0723"
ML100K_SHA256 = "50d2a982c66986937beb9ffb3aa76efe955bf3d5c6b761f4e3a7cd717c6a3229"

TRUTH_STATE = {
    "RESULT_STATUS": "NOT_RUN",
    "TEST_SET_OPENED": "NO",
    "ACCEPTED_RESULT_ROWS": 0,
    "execution_authorized": False,
    "benchmark_admission_opened": False,
    "phase_1e_complete": False,
    "project_benchmark_numbers": "INVALID_FOR_PAPER",
}

PACKET_FILES = [
    "dataset_materialization_packet.json",
    "environment_materialization_packet.json",
    "recbole_dataset_bridge_packet.json",
    "execution_boundary_and_negative_assertions.json",
    "audit_handoff.json",
]

DIRECT_REQUIREMENTS = [
    "pip==24.0",
    "setuptools==69.5.1",
    "wheel==0.43.0",
    "torch==2.2.2+cpu",
    "numpy==1.26.4",
    "scipy==1.11.4",
    "pandas==2.1.4",
    "scikit-learn==1.3.2",
    "PyYAML==6.0.2",
    "tqdm==4.66.5",
    "colorlog==4.7.2",
    "colorama==0.4.4",
    "texttable==1.7.0",
    "tensorboard==2.15.2",
    "ray==2.6.3",
    "thop==0.1.1.post2207130030",
    "tabulate==0.9.0",
    "plotly==5.18.0",
    "psutil==5.9.8",
]

ML100K_FILES = [
    "README",
    "allbut.pl",
    "mku.sh",
    "u.data",
    "u.genre",
    "u.info",
    "u.item",
    "u.occupation",
    "u.user",
    "u1.base",
    "u1.test",
    "u2.base",
    "u2.test",
    "u3.base",
    "u3.test",
    "u4.base",
    "u4.test",
    "u5.base",
    "u5.test",
    "ua.base",
    "ua.test",
    "ub.base",
    "ub.test",
]


def passport(label: str, dependencies: list[str]) -> dict[str, Any]:
    return {
        "origin_skill": "experiment-agent",
        "origin_mode": "design",
        "origin_date": CREATED_AT,
        "verification_status": "UNVERIFIED",
        "version_label": label,
        "upstream_dependencies": dependencies,
        "repro_lock": None,
        "experiment_intake_declaration": {
            "status": "no_experiments_declared",
            "declared_at": CREATED_AT,
            "declared_by": "scholar",
        },
        "experiment_provenance": [],
    }


def argv_hash(argv: list[str]) -> str:
    raw = json.dumps(argv, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def command(
    command_id: str,
    purpose: str,
    argv: list[str],
    *,
    network: bool,
    timeout_seconds: int,
    write_set: list[str],
    required_outputs: list[str],
    postconditions: list[str],
) -> dict[str, Any]:
    return {
        "id": command_id,
        "purpose": purpose,
        "argv": argv,
        "argv_sha256": argv_hash(argv),
        "network": network,
        "timeout_seconds": timeout_seconds,
        "write_set": write_set,
        "required_outputs": required_outputs,
        "postconditions": postconditions,
    }


def mount(source: str, target: str, readonly: bool) -> str:
    value = f"type=bind,src={source},dst={target}"
    return value + (",readonly" if readonly else "")


def docker_run_argv(
    mounts: list[tuple[str, str, bool]],
    program: str,
    args: list[str],
    *,
    network: bool,
    workdir: str,
) -> list[str]:
    network_mode = "bridge" if network else "none"
    argv = [
        DOCKER_EXE,
        "run",
        "--rm",
        "--pull=never",
        "--platform",
        "linux/amd64",
        "--network",
        network_mode,
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=536870912,mode=1777",
        "--user",
        "10001:10001",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "256",
        "--cpus",
        "2",
        "--memory",
        "4g",
        "--stop-timeout",
        "10",
        "--env",
        "HOME=/tmp/home",
        "--env",
        "PYTHONNOUSERSITE=1",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--env",
        "PIP_CONFIG_FILE=/dev/null",
        "--env",
        "PIP_DISABLE_PIP_VERSION_CHECK=1",
        "--env",
        "PIP_NO_CACHE_DIR=1",
    ]
    if not network:
        argv += ["--env", "PIP_NO_INDEX=1"]
    for source, target, readonly in mounts:
        argv += ["--mount", mount(source, target, readonly)]
    argv += ["--workdir", workdir, IMAGE_REF, program]
    argv += args
    return argv


DATASET_ACQUIRE_SCRIPT = r'''
import hashlib
import json
import os
import pathlib
import urllib.request

root = pathlib.Path('/stage1e/data')
specs = [
    ('provider_metadata/ml-100k-README.txt', 'https://files.grouplens.org/datasets/movielens/ml-100k-README.txt', 6748),
    ('provider_metadata/ml-100k.zip.md5', 'https://files.grouplens.org/datasets/movielens/ml-100k.zip.md5', 53),
    ('download/ml-100k.zip', 'https://files.grouplens.org/datasets/movielens/ml-100k.zip', 4924029),
]

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('REDIRECT_FORBIDDEN')

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
rows = []
for relative, url, expected_bytes in specs:
    final = root / relative
    partial = final.with_name(final.name + '.partial')
    final.parent.mkdir(parents=True, exist_ok=True)
    assert not final.exists() and not partial.exists()
    req = urllib.request.Request(url, headers={'User-Agent': 'stage1e-r6-c1r3/1.0'})
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    count = 0
    with opener.open(req, timeout=120) as response, partial.open('xb') as sink:
        assert response.status == 200
        assert response.geturl() == url
        declared = response.headers.get('Content-Length')
        assert declared is not None and int(declared) == expected_bytes
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            count += len(block)
            assert count <= expected_bytes
            md5.update(block)
            sha256.update(block)
            sink.write(block)
        sink.flush()
        os.fsync(sink.fileno())
    assert count == expected_bytes
    os.replace(partial, final)
    rows.append({'path': relative, 'url': url, 'bytes': count, 'md5': md5.hexdigest(), 'sha256': sha256.hexdigest(), 'redirects': 0})

by_path = {row['path']: row for row in rows}
archive = by_path['download/ml-100k.zip']
assert archive['md5'] == '0e33842e24a9c977be4e0107933c0723'
assert archive['sha256'] == '50d2a982c66986937beb9ffb3aa76efe955bf3d5c6b761f4e3a7cd717c6a3229'
sidecar = (root / 'provider_metadata/ml-100k.zip.md5').read_text(encoding='ascii').rstrip('\r\n')
assert sidecar == 'MD5 (ml-100k.zip) = 0e33842e24a9c977be4e0107933c0723'
receipt = {
    'schema_version': 'stage1e-r6-c1r3-ml100k-acquisition-1.0',
    'attempt': 'attempt-004-linux',
    'files': rows,
    'provider_sidecar_exact': sidecar,
    'archive_provider_md5_verified': True,
    'archive_frozen_sha256_verified': True,
    'network_phase_only': True,
    'verdict': 'PASS',
}
(root / 'receipts/dataset_acquisition.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
'''.strip()


DATASET_TRANSFORM_SCRIPT = r'''
import hashlib
import json
import os
import pathlib
import shutil
import stat
import zipfile

root = pathlib.Path('/stage1e/data')
archive = root / 'download/ml-100k.zip'
expected_names = ['README','allbut.pl','mku.sh','u.data','u.genre','u.info','u.item','u.occupation','u.user','u1.base','u1.test','u2.base','u2.test','u3.base','u3.test','u4.base','u4.test','u5.base','u5.test','ua.base','ua.test','ub.base','ub.test']
expected = {'ml-100k/' + name for name in expected_names}
stage = root / 'extract-staging'
raw = root / 'raw/ml-100k'
atomic_dir = root / 'recbole_atomic/ml-100k'
assert stage.is_dir() and not any(stage.iterdir())
assert not raw.exists()
atomic_dir.mkdir(parents=True, exist_ok=False)

seen = set()
seen_folded = set()
total = 0
with zipfile.ZipFile(archive) as zf:
    infos = zf.infolist()
    for info in infos:
        name = info.filename
        assert name and '\\' not in name and '\x00' not in name and not name.startswith('/') and ':' not in name
        parts = pathlib.PurePosixPath(name).parts
        assert '.' not in parts and '..' not in parts
        mode = (info.external_attr >> 16) & 0o170000
        assert mode not in (stat.S_IFLNK, stat.S_IFCHR, stat.S_IFBLK, stat.S_IFIFO, stat.S_IFSOCK)
        if info.is_dir():
            assert name == 'ml-100k/'
            continue
        assert name in expected and name not in seen and name.casefold() not in seen_folded
        seen.add(name)
        seen_folded.add(name.casefold())
        assert info.file_size <= 20_000_000
        total += info.file_size
        assert total <= 100_000_000
    assert seen == expected
    for info in infos:
        if info.is_dir():
            continue
        target = stage / pathlib.PurePosixPath(info.filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info, 'r') as source, target.open('xb') as sink:
            shutil.copyfileobj(source, sink, 1024 * 1024)
            sink.flush()
            os.fsync(sink.fileno())

extracted = stage / 'ml-100k'
physical = sorted((p for p in extracted.rglob('*') if p.is_file()), key=lambda p: p.name)
assert len(physical) == 23 and {p.name for p in physical} == set(expected_names)
assert not any(p.is_symlink() for p in extracted.rglob('*'))
raw.parent.mkdir(parents=True, exist_ok=True)
os.replace(extracted, raw)

inventory = []
for path in sorted(raw.iterdir(), key=lambda p: p.name):
    payload = path.read_bytes()
    inventory.append({'path': 'raw/ml-100k/' + path.name, 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
(root / 'receipts/extraction_inventory.json').write_text(json.dumps({'schema_version':'stage1e-r6-c1r3-ml100k-extraction-1.0','archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'file_count':len(inventory),'files':inventory,'safe_extraction_checks':'PASS'}, indent=2, sort_keys=True) + '\n', encoding='utf-8')

source = raw / 'u.data'
atomic = atomic_dir / 'ml-100k.inter'
users = {}
items = {}
raw_projection = hashlib.sha256()
atomic_projection = hashlib.sha256()
rows = 0
with source.open('rb') as reader, atomic.open('xb') as writer:
    writer.write(b'user_id:token\titem_id:token\trating:float\ttimestamp:float\n')
    for raw_line in reader:
        rows += 1
        line = raw_line.rstrip(b'\r\n')
        fields = line.split(b'\t')
        assert len(fields) == 4
        user, item, rating, timestamp = [field.decode('ascii') for field in fields]
        assert user.isdigit() and item.isdigit() and rating in {'1','2','3','4','5'} and timestamp.isdigit()
        users.setdefault(user, len(users) + 1)
        items.setdefault(item, len(items) + 1)
        projection = str(rows).encode('ascii') + b'\0' + b'\0'.join(fields) + b'\n'
        raw_projection.update(projection)
        writer.write(b'\t'.join(fields) + b'\n')
    writer.flush()
    os.fsync(writer.fileno())
assert rows == 100000 and len(users) == 943 and len(items) == 1682

with atomic.open('rb') as reader:
    assert reader.readline().rstrip(b'\r\n') == b'user_id:token\titem_id:token\trating:float\ttimestamp:float'
    atomic_rows = 0
    for raw_line in reader:
        atomic_rows += 1
        fields = raw_line.rstrip(b'\r\n').split(b'\t')
        assert len(fields) == 4
        atomic_projection.update(str(atomic_rows).encode('ascii') + b'\0' + b'\0'.join(fields) + b'\n')
assert atomic_rows == rows and atomic_projection.hexdigest() == raw_projection.hexdigest()

maps = {'schema_version':'stage1e-r6-c1r3-first-occurrence-maps-1.0','users':[{'raw_id':key,'ordinal':value} for key,value in users.items()],'items':[{'raw_id':key,'ordinal':value} for key,value in items.items()]}
(root / 'receipts/first_occurrence_id_maps.json').write_text(json.dumps(maps, indent=2, sort_keys=True) + '\n', encoding='utf-8')
reconciliation = {'schema_version':'stage1e-r6-c1r3-raw-atomic-reconciliation-1.0','rows_checked':rows,'users':len(users),'items':len(items),'raw_projection_sha256':raw_projection.hexdigest(),'atomic_projection_sha256':atomic_projection.hexdigest(),'projection_equal':True,'filtering':False,'deduplication':False,'sorting':False,'id_rewrite':False,'timestamp_rewrite':False,'verdict':'PASS'}
(root / 'receipts/raw_to_atomic_reconciliation.json').write_text(json.dumps(reconciliation, indent=2, sort_keys=True) + '\n', encoding='utf-8')
'''.strip()


DATASET_FINAL_SCRIPT = r'''
import hashlib
import json
import pathlib

root = pathlib.Path('/stage1e/data')
required = ['receipts/dataset_acquisition.json','receipts/extraction_inventory.json','receipts/first_occurrence_id_maps.json','receipts/raw_to_atomic_reconciliation.json','recbole_atomic/ml-100k/ml-100k.inter']
assert all((root / path).is_file() for path in required)
acquisition = json.loads((root / required[0]).read_text(encoding='utf-8'))
inventory = json.loads((root / required[1]).read_text(encoding='utf-8'))
reconciliation = json.loads((root / required[3]).read_text(encoding='utf-8'))
atomic = root / required[4]
assert acquisition['verdict'] == 'PASS' and inventory['file_count'] == 23
assert reconciliation['verdict'] == 'PASS' and reconciliation['projection_equal'] is True
assert reconciliation['rows_checked'] == 100000 and reconciliation['users'] == 943 and reconciliation['items'] == 1682
receipt = {'schema_version':'stage1e-r6-c1r3-dataset-materialization-1.0','attempt':'attempt-004-linux','archive_sha256':'50d2a982c66986937beb9ffb3aa76efe955bf3d5c6b761f4e3a7cd717c6a3229','atomic_path':'recbole_atomic/ml-100k/ml-100k.inter','atomic_bytes':atomic.stat().st_size,'atomic_sha256':hashlib.sha256(atomic.read_bytes()).hexdigest(),'rows':100000,'users':943,'items':1682,'scientific_execution_performed':False,'test_opened':False,'verdict':'PASS_R6_M0_MATERIALIZED_NOT_BENCHMARKED'}
(root / 'receipts/dataset_materialization.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
'''.strip()


WHEEL_MANIFEST_SCRIPT = r'''
import email
import hashlib
import json
import pathlib
import re
import zipfile

root = pathlib.Path('/stage1e/env')
wheelhouse = root / 'wheelhouse'
files = sorted(wheelhouse.iterdir(), key=lambda p: p.name.casefold())
assert files and all(p.is_file() and not p.is_symlink() and p.suffix == '.whl' for p in files)
forbidden = ('win32','win_amd64','macosx','aarch64','arm64','cu11','cu12','cuda','rocm')
assert not any(token in p.name.lower() for p in files for token in forbidden)
rows = []
requirements = []
seen = set()
for path in files:
    payload = path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        metadata = [name for name in archive.namelist() if name.endswith('.dist-info/METADATA')]
        assert len(metadata) == 1
        message = email.message_from_bytes(archive.read(metadata[0]))
    name = message['Name']
    version = message['Version']
    normalized = re.sub(r'[-_.]+', '-', name).lower()
    assert normalized not in seen and normalized != 'recbole'
    seen.add(normalized)
    digest = hashlib.sha256(payload).hexdigest()
    rows.append({'file':path.name,'bytes':len(payload),'sha256':digest,'name':name,'normalized_name':normalized,'version':version})
    requirements.append(f'{name}=={version} --hash=sha256:{digest}')

expected = {'pip':'24.0','setuptools':'69.5.1','wheel':'0.43.0','torch':'2.2.2+cpu','numpy':'1.26.4','scipy':'1.11.4','pandas':'2.1.4','scikit-learn':'1.3.2','pyyaml':'6.0.2','tqdm':'4.66.5','colorlog':'4.7.2','colorama':'0.4.4','texttable':'1.7.0','tensorboard':'2.15.2','ray':'2.6.3','thop':'0.1.1.post2207130030','tabulate':'0.9.0','plotly':'5.18.0','psutil':'5.9.8'}
actual = {row['normalized_name']: row['version'] for row in rows}
assert all(actual.get(name) == version for name,version in expected.items())
assert sum(1 for row in rows if row['normalized_name'] == 'torch' and row['version'] == '2.2.2+cpu') == 1
(root / 'receipts/wheelhouse_manifest.json').write_text(json.dumps({'schema_version':'stage1e-r6-c1r3-linux-wheelhouse-1.0','platform':'linux/amd64','python':'3.11.9','wheel_only':True,'cpu_only':True,'recbole_absent':True,'wheels':rows}, indent=2, sort_keys=True) + '\n', encoding='utf-8')
(root / 'receipts/hashed_third_party_requirements.txt').write_text('\n'.join(sorted(requirements, key=str.casefold)) + '\n', encoding='utf-8')
'''.strip()


SOURCE_STAGE_SCRIPT = r'''
import hashlib
import json
import pathlib

source = pathlib.Path('/stage1e/recbole-source')
root = pathlib.Path('/stage1e/env')
target = root / 'source-staging/recbole_v1_2_1_9a6f63d'
assert source.is_dir() and not target.exists()
paths = sorted((p for p in source.rglob('*') if p.is_file() and '.git' not in p.relative_to(source).parts), key=lambda p: p.relative_to(source).as_posix())
assert len(paths) == 265 and not any(p.is_symlink() for p in source.rglob('*'))
rows = []
for path in paths:
    relative = path.relative_to(source)
    payload = path.read_bytes()
    destination = target / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    copied = destination.read_bytes()
    assert copied == payload
    rows.append({'path':relative.as_posix(),'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()})
assert sum(row['bytes'] for row in rows) == 1541044
receipt = {'schema_version':'stage1e-r6-c1r3-recbole-source-staging-1.0','revision':'9a6f63d8d4a5b989fe27955a833f813a6d86041e','git_tree':'08915121fea069a30f7e3e97a72e16e7e76d43c6','source_manifest_git_blob_sha256':'c5794b9daccdd01ca600c6ef7f890918825fbbb872efa67036c4565234e87016','file_count':len(rows),'total_bytes':sum(row['bytes'] for row in rows),'files':rows,'source_destination_equal':True}
(root / 'receipts/recbole_source_staging.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
'''.strip()


LOCAL_WHEEL_SCRIPT = r'''
import email
import hashlib
import json
import pathlib
import zipfile

root = pathlib.Path('/stage1e/env')
wheels = list((root / 'local-wheel').glob('*.whl'))
assert len(wheels) == 1
path = wheels[0]
payload = path.read_bytes()
with zipfile.ZipFile(path) as archive:
    metadata = [name for name in archive.namelist() if name.endswith('.dist-info/METADATA')]
    assert len(metadata) == 1
    message = email.message_from_bytes(archive.read(metadata[0]))
assert message['Name'].lower() == 'recbole' and message['Version'] == '1.2.1'
digest = hashlib.sha256(payload).hexdigest()
receipt = {'schema_version':'stage1e-r6-c1r3-local-recbole-wheel-1.0','file':path.name,'bytes':len(payload),'sha256':digest,'name':message['Name'],'version':message['Version'],'revision':'9a6f63d8d4a5b989fe27955a833f813a6d86041e','git_tree':'08915121fea069a30f7e3e97a72e16e7e76d43c6','local_source_build':True}
(root / 'receipts/local_recbole_wheel.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
(root / 'receipts/hashed_local_recbole_requirement.txt').write_text(f'recbole==1.2.1 --hash=sha256:{digest}\n', encoding='utf-8')
'''.strip()


BUILD_SOURCE_SCRIPT = r'''
import hashlib
import json
import pathlib

root = pathlib.Path('/stage1e/env')
source = root / 'source-staging/recbole_v1_2_1_9a6f63d'
target = root / 'build-source/recbole_v1_2_1_9a6f63d'
assert source.is_dir() and not target.exists()
paths = sorted((p for p in source.rglob('*') if p.is_file()), key=lambda p: p.relative_to(source).as_posix())
assert len(paths) == 265 and not any(p.is_symlink() for p in source.rglob('*'))
rows = []
for path in paths:
    relative = path.relative_to(source)
    payload = path.read_bytes()
    destination = target / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    assert destination.read_bytes() == payload
    rows.append({'path':relative.as_posix(),'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()})
assert sum(row['bytes'] for row in rows) == 1541044
(root / 'receipts/recbole_build_source.json').write_text(json.dumps({'schema_version':'stage1e-r6-c1r3-recbole-build-source-1.0','file_count':len(rows),'total_bytes':sum(row['bytes'] for row in rows),'source_destination_equal':True,'immutable_staging_unchanged':True}, indent=2, sort_keys=True) + '\n', encoding='utf-8')
'''.strip()


ENVIRONMENT_FINAL_SCRIPT = r'''
import compileall
import importlib.metadata
import json
import pathlib
import platform
import subprocess
import sys

root = pathlib.Path('/stage1e/env')
check = subprocess.run([sys.executable,'-B','-I','-m','pip','check'], text=True, capture_output=True, timeout=180)
assert check.returncode == 0
inventory = sorted(({'name':dist.metadata['Name'],'version':dist.version} for dist in importlib.metadata.distributions()), key=lambda row: row['name'].casefold())
import numpy
import pandas
import recbole
import scipy
import sklearn
import torch
assert platform.python_version() == '3.11.9'
assert recbole.__version__ == '1.2.1'
assert torch.__version__ == '2.2.2+cpu' and torch.version.cuda is None and not torch.cuda.is_available()
stage = root / 'source-staging/recbole_v1_2_1_9a6f63d'
python_files = sorted(stage.rglob('*.py'), key=lambda p: p.as_posix())
total = 0
for path in python_files:
    payload = path.read_bytes()
    total += len(payload)
    compile(payload, str(path), 'exec', dont_inherit=True, optimize=0)
assert len(python_files) == 150 and total == 1378341
assert not list(stage.rglob('__pycache__')) and not list(stage.rglob('*.pyc'))
receipt = {'schema_version':'stage1e-r6-c1r3-environment-materialization-1.0','attempt':'attempt-004-linux','python':platform.python_version(),'executable':sys.executable,'recbole':recbole.__version__,'torch':torch.__version__,'torch_cuda':torch.version.cuda,'cuda_available':torch.cuda.is_available(),'numpy':numpy.__version__,'scipy':scipy.__version__,'pandas':pandas.__version__,'sklearn':sklearn.__version__,'pip_check_stdout':check.stdout,'pip_check_stderr':check.stderr,'packages':inventory,'source_python_files':len(python_files),'source_python_bytes':total,'dataset_constructed':False,'training':False,'evaluation':False,'test_opened':False,'verdict':'PASS_R6_M1_ENVIRONMENT_MATERIALIZED_NOT_BENCHMARKED'}
(root / 'receipts/environment_materialization.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
'''.strip()


BRIDGE_PLAN_SCRIPT = r'''
import hashlib
import importlib.util
import json
import pathlib

data_root = pathlib.Path('/stage1e/data')
env_root = pathlib.Path('/stage1e/env')
source = data_root / 'recbole_atomic/ml-100k/ml-100k.inter'
spec = importlib.util.find_spec('recbole')
assert spec is not None and spec.submodule_search_locations
package_root = pathlib.Path(next(iter(spec.submodule_search_locations))).resolve()
target_dir = package_root / 'dataset_example/ml-100k'
assert source.is_file() and not target_dir.exists()
receipt = {'schema_version':'stage1e-r6-c1r3-bridge-plan-1.0','source':'/stage1e/data/recbole_atomic/ml-100k/ml-100k.inter','source_bytes':source.stat().st_size,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'package_root':str(package_root),'target_directory':str(target_dir),'target_absent':True,'dataset_loaded':False}
(env_root / 'receipts/bridge_plan.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
'''.strip()


BRIDGE_COPY_SCRIPT = r'''
import hashlib
import importlib.util
import json
import pathlib

data_root = pathlib.Path('/stage1e/data')
env_root = pathlib.Path('/stage1e/env')
source = data_root / 'recbole_atomic/ml-100k/ml-100k.inter'
spec = importlib.util.find_spec('recbole')
package_root = pathlib.Path(next(iter(spec.submodule_search_locations))).resolve()
target_dir = package_root / 'dataset_example/ml-100k'
target = target_dir / 'ml-100k.inter'
assert not target_dir.exists()
payload = source.read_bytes()
assert payload.count(b'\n') == 100001
target_dir.mkdir(parents=True, exist_ok=False)
target.write_bytes(payload)
copied = target.read_bytes()
assert copied == payload
receipt = {'schema_version':'stage1e-r6-c1r3-bridge-copy-1.0','source_bytes':len(payload),'target_bytes':len(copied),'source_sha256':hashlib.sha256(payload).hexdigest(),'target_sha256':hashlib.sha256(copied).hexdigest(),'row_count':100000,'header_count':1,'destination_exact_file_set':['ml-100k.inter'],'binary_equal':True,'dataset_loaded':False,'network_used':False,'verdict':'PASS'}
(env_root / 'receipts/bridge_copy.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
'''.strip()


BRIDGE_CONFIG_SCRIPT = r'''
import json
import pathlib
from recbole.config import Config

root = pathlib.Path('/stage1e/env')
config = Config(model='BPR', dataset='ml-100k', config_dict={'use_gpu':False})
resolved = pathlib.Path(config['data_path']).resolve()
expected = pathlib.Path(config.__class__.__module__.replace('.', '/'))
assert resolved.name == 'ml-100k'
assert (resolved / 'ml-100k.inter').is_file()
receipt = {'schema_version':'stage1e-r6-c1r3-config-path-check-1.0','dataset':'ml-100k','model':'BPR','resolved_data_path':str(resolved),'exact_file_set':sorted(path.name for path in resolved.iterdir()),'dataset_constructed':False,'training':False,'evaluation':False,'test_opened':False,'verdict':'PASS'}
assert receipt['exact_file_set'] == ['ml-100k.inter']
(root / 'receipts/config_path_check.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
'''.strip()


def image_commands() -> list[dict[str, Any]]:
    pull = [DOCKER_EXE, "pull", "--platform", "linux/amd64", IMAGE_REF]
    inspect = [DOCKER_EXE, "image", "inspect", IMAGE_REF]
    probe = docker_run_argv(
        [],
        "/usr/local/bin/python",
        [
            "-B",
            "-I",
            "-c",
            "import json,platform,sys; print(json.dumps({'python':platform.python_version(),'implementation':platform.python_implementation(),'machine':platform.machine(),'platform':sys.platform,'executable':sys.executable},sort_keys=True))",
        ],
        network=False,
        workdir="/tmp",
    )
    return [
        command(
            "I00_PULL_EXACT_OFFICIAL_PLATFORM_MANIFEST",
            "Acquire only the unique official Python platform manifest by immutable digest.",
            pull,
            network=True,
            timeout_seconds=1800,
            write_set=["Docker Desktop image store: exact manifest and referenced layers only"],
            required_outputs=["successful immutable-digest pull receipt"],
            postconditions=["linux/amd64 only", "no tag fallback", "no build", "no container created"],
        ),
        command(
            "I01_INSPECT_LOCAL_IMAGE_IDENTITY",
            "Capture local image ID, RepoDigests, OS, architecture and config without network.",
            inspect,
            network=False,
            timeout_seconds=120,
            write_set=[],
            required_outputs=["typed IMAGE_IDENTITY_V1 adapter receipt"],
            postconditions=["manifest digest exact", "OS linux", "architecture amd64", "local image ID sha256 recorded"],
        ),
        command(
            "I02_PROBE_EXACT_CPYTHON_IDENTITY",
            "Run one read-only offline identity probe in the exact image.",
            probe,
            network=False,
            timeout_seconds=120,
            write_set=[],
            required_outputs=["typed PYTHON_RUNTIME_IDENTITY_V1 adapter receipt"],
            postconditions=["CPython 3.11.9", "linux/amd64", "no mount", "container removed"],
        ),
    ]


def dataset_commands() -> list[dict[str, Any]]:
    rw = [(DATA_ROOT, "/stage1e/data", False)]
    return [
        command(
            "M00_ACQUIRE_OFFICIAL_GROUPLENS_BYTES",
            "Acquire three exact official GroupLens objects and verify size, sidecar, MD5 and frozen SHA-256 before promotion.",
            docker_run_argv(rw, "/usr/local/bin/python", ["-B", "-I", "-c", DATASET_ACQUIRE_SCRIPT], network=True, workdir="/stage1e/data"),
            network=True,
            timeout_seconds=1800,
            write_set=["download/ml-100k.zip", "provider_metadata/*", "receipts/dataset_acquisition.json"],
            required_outputs=["typed DATASET_ACQUISITION_V1 receipt"],
            postconditions=["exact official URLs", "redirects zero", "archive bytes/MD5/SHA-256 exact", "no fallback"],
        ),
        command(
            "M01_SAFE_EXTRACT_CONVERT_AND_RECONCILE",
            "Safely extract the exact archive inventory, preserve all interaction rows and build the RecBole atomic file offline.",
            docker_run_argv(rw, "/usr/local/bin/python", ["-B", "-I", "-c", DATASET_TRANSFORM_SCRIPT], network=False, workdir="/stage1e/data"),
            network=False,
            timeout_seconds=1800,
            write_set=["extract-staging/**", "raw/ml-100k/**", "recbole_atomic/ml-100k/ml-100k.inter", "receipts/extraction_inventory.json", "receipts/first_occurrence_id_maps.json", "receipts/raw_to_atomic_reconciliation.json"],
            required_outputs=["typed DATASET_TRANSFORMATION_V1 receipt set"],
            postconditions=["23 safe files", "100000 rows", "943 users", "1682 items", "ordinal lexical equality", "no filtering/deduplication/sorting/ID rewrite"],
        ),
        command(
            "M02_SEAL_DATASET_MATERIALIZATION_RECEIPT",
            "Re-read lane receipts and seal one typed dataset materialization receipt without loading RecBole.",
            docker_run_argv(rw, "/usr/local/bin/python", ["-B", "-I", "-c", DATASET_FINAL_SCRIPT], network=False, workdir="/stage1e/data"),
            network=False,
            timeout_seconds=300,
            write_set=["receipts/dataset_materialization.json"],
            required_outputs=["typed DATASET_MATERIALIZATION_V1 receipt"],
            postconditions=["all upstream receipts PASS", "atomic file hash bound", "scientific execution false", "TEST unopened"],
        ),
    ]


def environment_commands() -> list[dict[str, Any]]:
    env_rw = [(ENV_ROOT, "/stage1e/env", False)]
    env_source = [(ENV_ROOT, "/stage1e/env", False), (SOURCE_ROOT, "/stage1e/recbole-source", True)]
    download_argv = docker_run_argv(
        env_rw,
        "/usr/local/bin/python",
        [
            "-B",
            "-I",
            "-m",
            "pip",
            "--isolated",
            "download",
            "--only-binary=:all:",
            "--dest",
            "/stage1e/env/wheelhouse",
            "--index-url",
            "https://download.pytorch.org/whl/cpu",
            "--extra-index-url",
            "https://pypi.org/simple",
            *DIRECT_REQUIREMENTS,
        ],
        network=True,
        workdir="/stage1e/env",
    )
    create_venv = docker_run_argv(env_rw, "/usr/local/bin/python", ["-B", "-I", "-m", "venv", "--copies", "/stage1e/env/venv"], network=False, workdir="/stage1e/env")
    install_third_party = docker_run_argv(
        env_rw,
        "/stage1e/env/venv/bin/python",
        ["-B", "-I", "-m", "pip", "--isolated", "install", "--require-hashes", "--only-binary=:all:", "--no-index", "--find-links", "/stage1e/env/wheelhouse", "-r", "/stage1e/env/receipts/hashed_third_party_requirements.txt"],
        network=False,
        workdir="/stage1e/env",
    )
    build_local = docker_run_argv(
        env_rw,
        "/stage1e/env/venv/bin/python",
        ["-B", "-I", "-m", "pip", "--isolated", "wheel", "--no-deps", "--no-build-isolation", "--no-index", "--wheel-dir", "/stage1e/env/local-wheel", "/stage1e/env/build-source/recbole_v1_2_1_9a6f63d"],
        network=False,
        workdir="/stage1e/env",
    )
    install_local = docker_run_argv(
        env_rw,
        "/stage1e/env/venv/bin/python",
        ["-B", "-I", "-m", "pip", "--isolated", "install", "--no-deps", "--require-hashes", "--only-binary=:all:", "--no-index", "--find-links", "/stage1e/env/local-wheel", "-r", "/stage1e/env/receipts/hashed_local_recbole_requirement.txt"],
        network=False,
        workdir="/stage1e/env",
    )
    return [
        command("E00_DOWNLOAD_LINUX_WHEEL_CLOSURE", "Resolve and download a wheel-only CPython 3.11 Linux/amd64 CPU closure from the two approved indexes.", download_argv, network=True, timeout_seconds=3600, write_set=["wheelhouse/*.whl"], required_outputs=["complete wheel-only closure"], postconditions=["direct pins exact", "torch 2.2.2+cpu", "no source distributions", "no RecBole distribution"]),
        command("E01_HASH_AND_FREEZE_WHEEL_CLOSURE", "Hash every wheel, read wheel METADATA and write a complete hash-locked offline closure.", docker_run_argv(env_rw, "/usr/local/bin/python", ["-B", "-I", "-c", WHEEL_MANIFEST_SCRIPT], network=False, workdir="/stage1e/env"), network=False, timeout_seconds=600, write_set=["receipts/wheelhouse_manifest.json", "receipts/hashed_third_party_requirements.txt"], required_outputs=["typed WHEEL_CLOSURE_V1 receipt", "hash-locked requirements"], postconditions=["all files wheels", "direct versions exact", "no GPU/foreign-platform/RecBole artifact"]),
        command("E02_CREATE_EXACT_CONTAINER_VENV", "Create the CPython 3.11.9 venv at its stable in-container path.", create_venv, network=False, timeout_seconds=600, write_set=["venv/**"], required_outputs=["/stage1e/env/venv/bin/python"], postconditions=["CPython base image only", "copies mode", "no host Python installer"]),
        command("E03_INSTALL_HASHED_THIRD_PARTY_CLOSURE", "Install only the frozen wheelhouse offline with hashes required.", install_third_party, network=False, timeout_seconds=1800, write_set=["venv/**"], required_outputs=["installed third-party closure"], postconditions=["no index", "hash required", "wheel-only", "RecBole absent"]),
        command("E04_STAGE_VERIFIED_RECBOLE_SOURCE", "Copy the host-verified 265-file official RecBole source into immutable attempt staging.", docker_run_argv(env_source, "/usr/local/bin/python", ["-B", "-I", "-c", SOURCE_STAGE_SCRIPT], network=False, workdir="/stage1e/env"), network=False, timeout_seconds=900, write_set=["source-staging/recbole_v1_2_1_9a6f63d/**", "receipts/recbole_source_staging.json"], required_outputs=["typed RECBOLE_SOURCE_STAGING_V1 receipt"], postconditions=["265 files", "1541044 bytes", "source mount read-only", "source and destination bytes equal"]),
        command("E05_PREPARE_EPHEMERAL_BUILD_SOURCE", "Copy immutable staged source to a separate ephemeral build root and reverify every byte.", docker_run_argv(env_rw, "/usr/local/bin/python", ["-B", "-I", "-c", BUILD_SOURCE_SCRIPT], network=False, workdir="/stage1e/env"), network=False, timeout_seconds=900, write_set=["build-source/recbole_v1_2_1_9a6f63d/**", "receipts/recbole_build_source.json"], required_outputs=["verified ephemeral build source"], postconditions=["265 files", "1541044 bytes", "immutable staging unchanged"]),
        command("E06_BUILD_LOCAL_RECBOLE_WHEEL", "Build one non-editable local wheel offline from the separately verified ephemeral copy.", build_local, network=False, timeout_seconds=1800, write_set=["build-source/recbole_v1_2_1_9a6f63d/build/**", "build-source/recbole_v1_2_1_9a6f63d/recbole.egg-info/**", "local-wheel/*.whl"], required_outputs=["one recbole 1.2.1 wheel"], postconditions=["no dependencies", "no build isolation", "no index", "no editable install", "immutable staging unchanged"]),
        command("E07_HASH_LOCAL_RECBOLE_WHEEL", "Bind the local wheel to official source revision/tree and produce one hash-locked requirement.", docker_run_argv(env_rw, "/usr/local/bin/python", ["-B", "-I", "-c", LOCAL_WHEEL_SCRIPT], network=False, workdir="/stage1e/env"), network=False, timeout_seconds=300, write_set=["receipts/local_recbole_wheel.json", "receipts/hashed_local_recbole_requirement.txt"], required_outputs=["typed LOCAL_RECBOLE_WHEEL_V1 receipt"], postconditions=["one wheel", "name/version exact", "revision/tree recorded", "SHA-256 recorded"]),
        command("E08_INSTALL_HASHED_LOCAL_RECBOLE_WHEEL", "Install only the hash-locked local RecBole wheel offline.", install_local, network=False, timeout_seconds=900, write_set=["venv/**"], required_outputs=["local RecBole installation"], postconditions=["no index", "no dependencies", "hash required", "not PyPI/editable/VCS"]),
        command("E09_SEAL_ENVIRONMENT_AND_IMPORT_CHECK", "Run pip check, freeze installed inventory, verify CPU imports and compile staged source in memory.", docker_run_argv(env_rw, "/stage1e/env/venv/bin/python", ["-B", "-I", "-c", ENVIRONMENT_FINAL_SCRIPT], network=False, workdir="/stage1e/env"), network=False, timeout_seconds=1200, write_set=["receipts/environment_materialization.json"], required_outputs=["typed ENVIRONMENT_MATERIALIZATION_V1 receipt"], postconditions=["pip check PASS", "Python 3.11.9", "RecBole 1.2.1", "torch 2.2.2+cpu", "150 source files compiled in memory", "no scientific execution"]),
        command("E10_ASSERT_ATTEMPT_WRITE_BOUNDARY", "Inventory the attempt root and bind every file to the declared lane write set.", docker_run_argv(env_rw, "/usr/local/bin/python", ["-B", "-I", "-c", "import hashlib,json,pathlib; r=pathlib.Path('/stage1e/env'); rows=[{'path':p.relative_to(r).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted((x for x in r.rglob('*') if x.is_file()),key=lambda x:x.as_posix())]; (r/'receipts/environment_attempt_inventory.json').write_text(json.dumps({'schema_version':'stage1e-r6-c1r3-environment-inventory-1.0','files':rows,'file_count':len(rows)},indent=2,sort_keys=True)+'\\n',encoding='utf-8')"], network=False, workdir="/stage1e/env"), network=False, timeout_seconds=1200, write_set=["receipts/environment_attempt_inventory.json"], required_outputs=["typed ATTEMPT_INVENTORY_V1 receipt"], postconditions=["ordinary files only", "all prior files SHA-256 bound", "no path outside attempt root"]),
    ]


def bridge_commands() -> list[dict[str, Any]]:
    mounts = [(DATA_ROOT, "/stage1e/data", True), (ENV_ROOT, "/stage1e/env", False)]
    return [
        command("B00_RESOLVE_PACKAGE_AND_REQUIRE_ABSENT_TARGET", "Resolve installed-package root without loading data and require the bridge target to be absent.", docker_run_argv(mounts, "/stage1e/env/venv/bin/python", ["-B", "-I", "-c", BRIDGE_PLAN_SCRIPT], network=False, workdir="/stage1e/env"), network=False, timeout_seconds=300, write_set=["receipts/bridge_plan.json"], required_outputs=["typed BRIDGE_PLAN_V1 receipt"], postconditions=["source present", "target absent", "dataset not loaded"]),
        command("B01_COPY_CANONICAL_ATOMIC_FILE", "Binary-copy only the canonical GroupLens-derived atomic file into the installed-package path.", docker_run_argv(mounts, "/stage1e/env/venv/bin/python", ["-B", "-I", "-c", BRIDGE_COPY_SCRIPT], network=False, workdir="/stage1e/env"), network=False, timeout_seconds=600, write_set=["venv/lib/python3.11/site-packages/recbole/dataset_example/ml-100k/ml-100k.inter", "receipts/bridge_copy.json"], required_outputs=["typed BRIDGE_COPY_V1 receipt"], postconditions=["source mount read-only", "source/destination bytes and SHA-256 equal", "exact one-file target", "100000 data rows"]),
        command("B02_CONFIG_ONLY_PATH_ASSERTION", "Instantiate configuration only and prove the forced ml-100k path resolves to the bridged one-file directory.", docker_run_argv(mounts, "/stage1e/env/venv/bin/python", ["-B", "-I", "-c", BRIDGE_CONFIG_SCRIPT], network=False, workdir="/stage1e/env"), network=False, timeout_seconds=300, write_set=["receipts/config_path_check.json"], required_outputs=["typed CONFIG_PATH_V1 receipt"], postconditions=["resolved path exact", "one .inter file", "no data load/training/evaluation/TEST"]),
    ]


def make_documents() -> dict[str, dict[str, Any]]:
    image = image_commands()
    dataset = dataset_commands()
    environment = environment_commands()
    bridge = bridge_commands()
    upstream = ["stage1e_e4_r6_pc2w_g1_backend_admission_v1", "ars_codex_academic_research_suite_0.1.26"]

    image_lock = {
        "registry": "docker.io",
        "repository": "library/python",
        "official_image": True,
        "historical_tag_evidence_only": IMAGE_TAG,
        "floating_tag_execution_allowed": False,
        "immutable_execution_reference": IMAGE_REF,
        "index_digest": IMAGE_INDEX_DIGEST,
        "platform_manifest_digest": IMAGE_MANIFEST_DIGEST,
        "os": "linux",
        "architecture": "amd64",
        "python_version": "3.11.9",
        "compressed_size_source_observation": "46.46 MB",
        "source_url": IMAGE_SOURCE_URL,
        "official_overview_url": "https://hub.docker.com/_/python",
        "license_statement": "Python license plus licenses of bundled Debian components; compliance remains the image user's responsibility.",
        "security_boundary": "TRUSTED_PINNED_RESEARCH_CODE_ONLY_NOT_HOSTILE_CODE_ISOLATION",
        "historical_image_risk": "Known-vulnerability metadata exists on the registry page; use is bounded, offline after acquisition, non-root and not represented as a security boundary.",
        "local_image_id": "UNRESOLVED_UNTIL_AUTHORIZED_I01",
        "candidate_fallback": None,
    }

    dataset_doc = {
        "schema_version": "stage1e-r6-c1r3-linux-dataset-materialization-packet-1.0",
        "created_at": CREATED_AT,
        "stage_id": STAGE_ID,
        "packet_id": "R6-C1R3-LINUX-DATASET-MATERIALIZATION-PACKET",
        "material_passport": passport("stage1e_e4_r6_c1r3_linux_dataset_packet_v1", upstream),
        "proposal_only": True,
        "execution_performed": False,
        "execution_authorized": False,
        "attempt": "attempt-004-linux",
        "roots": {"host_attempt_root": DATA_ROOT, "container_attempt_root": "/stage1e/data"},
        "official_identity": {
            "provider": "GroupLens Research Project, University of Minnesota",
            "dataset": "MovieLens 100K",
            "release_label": "released 4/1998",
            "readme_url": ML100K_README_URL,
            "checksum_url": ML100K_MD5_URL,
            "archive_url": ML100K_URL,
            "archive_expected_bytes": ML100K_BYTES,
            "provider_md5": ML100K_MD5,
            "locally_recomputed_frozen_sha256": ML100K_SHA256,
            "sha256_semantics": "LOCALLY_RECOMPUTED_FROM_PRIOR_OFFICIAL_ACQUISITION_NOT_PROVIDER_PUBLISHED",
        },
        "safe_zip_contract": {"expected_prefix": "ml-100k/", "exact_files": ML100K_FILES, "exact_file_count": 23, "maximum_member_uncompressed_bytes": 20_000_000, "maximum_total_uncompressed_bytes": 100_000_000, "links_devices_traversal_duplicates_case_collisions_allowed": False},
        "frozen_transformation": {"input": "raw/ml-100k/u.data", "output": "recbole_atomic/ml-100k/ml-100k.inter", "header": "user_id:token\titem_id:token\trating:float\ttimestamp:float", "input_rows": 100_000, "output_rows": 100_000, "users": 943, "items": 1682, "row_order_preserved": True, "filtering_deduplication_sorting_id_or_timestamp_rewrite": False},
        "commands": dataset,
        "command_order": [row["id"] for row in dataset],
        "command_count": len(dataset),
        "runner_root_initialization": {"performed_by_future_locked_central_runner": True, "create_new_only": True, "required_directories": ["download", "provider_metadata", "extract-staging", "raw", "recbole_atomic", "receipts"], "root_must_be_absent": True, "no_cleanup_retry_or_reuse": True},
        "resource_bounds": {"maximum_parallel_commands_in_lane": 1, "maximum_resident_memory_bytes_per_container": 4_294_967_296, "cpus": 2, "pids": 256, "retry_count": 0},
        "negative_assertions": {"recbole_dataset_constructed_or_loaded": False, "preprocessing_beyond_canonical_format_conversion": False, "training": False, "evaluation": False, "metrics": False, "test_opened": False, "benchmark_admission": False},
        "truth_state": TRUTH_STATE,
    }

    environment_doc = {
        "schema_version": "stage1e-r6-c1r3-linux-environment-materialization-packet-1.0",
        "created_at": CREATED_AT,
        "stage_id": STAGE_ID,
        "packet_id": "R6-C1R3-LINUX-ENVIRONMENT-MATERIALIZATION-PACKET",
        "material_passport": passport("stage1e_e4_r6_c1r3_linux_environment_packet_v1", upstream),
        "proposal_only": True,
        "execution_performed": False,
        "execution_authorized": False,
        "attempt": "attempt-004-linux",
        "roots": {"host_attempt_root": ENV_ROOT, "container_attempt_root": "/stage1e/env", "host_recbole_source_root": SOURCE_ROOT, "container_recbole_source_root": "/stage1e/recbole-source"},
        "base_image_lock": image_lock,
        "docker_client_lock": {"path": DOCKER_EXE, "bytes": DOCKER_EXE_BYTES, "sha256": DOCKER_EXE_SHA256, "observed_version": "29.5.3"},
        "direct_requirements": DIRECT_REQUIREMENTS,
        "direct_requirement_count": len(DIRECT_REQUIREMENTS),
        "recbole_source_lock": {"revision": RECBOLE_COMMIT, "git_tree": RECBOLE_TREE, "source_root": SOURCE_ROOT, "selected_manifest": SOURCE_MANIFEST, "selected_manifest_git_blob_bytes": RECBOLE_MANIFEST_BYTES, "selected_manifest_git_blob_sha256": RECBOLE_MANIFEST_SHA256, "selected_file_count": RECBOLE_FILE_COUNT, "selected_total_bytes": RECBOLE_TOTAL_BYTES, "selected_python_file_count": RECBOLE_PY_FILE_COUNT, "selected_python_total_bytes": RECBOLE_PY_TOTAL_BYTES, "pypi_editable_or_unpinned_vcs_allowed": False},
        "commands": environment,
        "command_order": [row["id"] for row in environment],
        "command_count": len(environment),
        "runner_root_initialization": {"performed_by_future_locked_central_runner": True, "create_new_only": True, "required_directories": ["wheelhouse", "source-staging", "build-source", "local-wheel", "receipts"], "venv_directory_created_by_E02_not_preflight": True, "root_must_be_absent": True, "no_cleanup_retry_or_reuse": True},
        "unresolved_until_authorized_materialization": ["local image ID", "resolved transitive wheel identities and hashes", "local RecBole wheel hash", "installed package inventory"],
        "resource_bounds": {"maximum_parallel_commands_in_lane": 1, "maximum_resident_memory_bytes_per_container": 4_294_967_296, "cpus": 2, "pids": 256, "minimum_C_free_bytes_before_I00": 21_474_836_480, "minimum_E_free_bytes_before_root_creation": 53_687_091_200, "retry_count": 0},
        "negative_assertions": {"host_python_installer_invoked": False, "ambient_host_python_used_for_environment": False, "source_distribution_allowed": False, "editable_or_PyPI_RecBole_allowed": False, "training": False, "evaluation": False, "metrics": False, "test_opened": False, "benchmark_admission": False},
        "truth_state": TRUTH_STATE,
    }

    bridge_doc = {
        "schema_version": "stage1e-r6-c1r3-linux-recbole-dataset-bridge-packet-1.0",
        "created_at": CREATED_AT,
        "stage_id": STAGE_ID,
        "packet_id": "R6-C1R3-LINUX-RECBOLE-DATASET-BRIDGE-PACKET",
        "material_passport": passport("stage1e_e4_r6_c1r3_linux_bridge_packet_v1", upstream),
        "proposal_only": True,
        "execution_performed": False,
        "execution_authorized": False,
        "execution_gate": {"dataset_materialization_receipt_required": True, "environment_materialization_receipt_required": True, "both_receipts_must_be_committed_strict_json_and_hash_bound": True, "attempt_pairing": "attempt-004-linux/attempt-004-linux", "cross_attempt_pairing_allowed": False, "current_status": "BLOCKED_PENDING_R6_M0_AND_R6_M1"},
        "pairing": {"dataset_host_root": DATA_ROOT, "environment_host_root": ENV_ROOT, "dataset_container_root": "/stage1e/data", "environment_container_root": "/stage1e/env", "canonical_source_file": "/stage1e/data/recbole_atomic/ml-100k/ml-100k.inter", "destination_relative_to_installed_recbole": "dataset_example/ml-100k/ml-100k.inter"},
        "commands": bridge,
        "command_order": [row["id"] for row in bridge],
        "command_count": len(bridge),
        "bridge_contract": {"copy_mode": "binary", "destination_exact_file_set": ["ml-100k.inter"], "expected_data_rows": 100_000, "source_destination_byte_count_equal_required": True, "source_destination_sha256_equal_required": True, "target_must_be_absent": True, "source_modification_allowed": False, "item_or_user_files_allowed": False, "links_allowed": False, "recbole_s3_or_any_network_allowed": False},
        "resource_bounds": {"maximum_parallel_commands": 1, "maximum_resident_memory_bytes_per_container": 4_294_967_296, "retry_count": 0},
        "negative_assertions": {"currently_executable": False, "dataset_constructed_or_loaded": False, "training": False, "evaluation": False, "split_generated": False, "metrics": False, "test_opened": False, "benchmark_admission": False},
        "truth_state": TRUTH_STATE,
    }

    adapters = [
        {"schema_id":"IMAGE_IDENTITY_V1","producer":"I01_INSPECT_LOCAL_IMAGE_IDENTITY","required_fields":{"Id":"sha256-string","RepoDigests":"array[string]","Os":"literal:linux","Architecture":"literal:amd64"},"invariants":["requested manifest digest exact","local image ID recorded","single inspected object"]},
        {"schema_id":"PYTHON_RUNTIME_IDENTITY_V1","producer":"I02_PROBE_EXACT_CPYTHON_IDENTITY","required_fields":{"python":"literal:3.11.9","implementation":"literal:CPython","machine":"enum:x86_64|AMD64","platform":"literal:linux","executable":"literal:/usr/local/bin/python"},"invariants":["stdout exactly one strict JSON object"]},
        {"schema_id":"DATASET_ACQUISITION_V1","producer":"M00_ACQUIRE_OFFICIAL_GROUPLENS_BYTES","required_fields":{"files":"array[3]","archive_provider_md5_verified":"literal:true","archive_frozen_sha256_verified":"literal:true","verdict":"literal:PASS"},"invariants":["exact URLs","redirects zero","byte counts exact"]},
        {"schema_id":"DATASET_MATERIALIZATION_V1","producer":"M02_SEAL_DATASET_MATERIALIZATION_RECEIPT","required_fields":{"rows":"literal:100000","users":"literal:943","items":"literal:1682","atomic_sha256":"sha256-string","scientific_execution_performed":"literal:false","verdict":"literal:PASS_R6_M0_MATERIALIZED_NOT_BENCHMARKED"},"invariants":["raw-to-atomic projection equal","TEST unopened"]},
        {"schema_id":"WHEEL_CLOSURE_V1","producer":"E01_HASH_AND_FREEZE_WHEEL_CLOSURE","required_fields":{"platform":"literal:linux/amd64","python":"literal:3.11.9","wheel_only":"literal:true","cpu_only":"literal:true","recbole_absent":"literal:true","wheels":"nonempty-array"},"invariants":["one normalized project per wheel","every wheel SHA-256 bound","all direct pins exact"]},
        {"schema_id":"ENVIRONMENT_MATERIALIZATION_V1","producer":"E09_SEAL_ENVIRONMENT_AND_IMPORT_CHECK","required_fields":{"python":"literal:3.11.9","recbole":"literal:1.2.1","torch":"literal:2.2.2+cpu","cuda_available":"literal:false","source_python_files":"literal:150","verdict":"literal:PASS_R6_M1_ENVIRONMENT_MATERIALIZED_NOT_BENCHMARKED"},"invariants":["pip check exit zero","source compiled in memory","no Dataset/training/evaluation"]},
        {"schema_id":"BRIDGE_COPY_V1","producer":"B01_COPY_CANONICAL_ATOMIC_FILE","required_fields":{"source_sha256":"sha256-string","target_sha256":"sha256-string","row_count":"literal:100000","binary_equal":"literal:true","verdict":"literal:PASS"},"invariants":["source and target hashes equal","destination exact one-file set","network false"]},
    ]

    all_commands = image + dataset + environment + bridge
    boundary_doc = {
        "schema_version": "stage1e-r6-c1r3-linux-execution-boundary-1.0",
        "created_at": CREATED_AT,
        "stage_id": STAGE_ID,
        "packet_id": "R6-C1R3-LINUX-EXECUTION-BOUNDARY",
        "material_passport": passport("stage1e_e4_r6_c1r3_linux_boundary_v1", upstream),
        "proposal_only": True,
        "execution_performed": False,
        "execution_authorized": False,
        "authoritative_entry_commit": "a939692d72d5d33cf67a8762d5260f2378df64f6",
        "g1_receipt": {"path": G1_RECEIPT, "git_blob_bytes": 6003, "git_blob_sha256": "7fac9ee1377ad183f12d3acb04061700d5218642d809dd54fe35ad79388605b1", "verdict": "PASS_R6_PC2W_G1_CURRENT_HOST_BACKEND_ADMITTED_FOR_TRUSTED_PINNED_PACKET_DESIGN_ONLY"},
        "source_locks": {"image": image_lock, "dataset": dataset_doc["official_identity"], "recbole": environment_doc["recbole_source_lock"]},
        "image_acquisition_and_probe_commands": image,
        "packet_files": PACKET_FILES,
        "command_counts": {"image": len(image), "dataset": len(dataset), "environment": len(environment), "bridge": len(bridge), "total": len(all_commands)},
        "network_command_ids": [row["id"] for row in all_commands if row["network"]],
        "execution_order": {"serial_prefix": [row["id"] for row in image], "parallel_lanes_after_image_probe": {"dataset": [row["id"] for row in dataset], "environment": [row["id"] for row in environment]}, "bridge_after_committed_lane_receipts": [row["id"] for row in bridge], "maximum_aggregate_concurrency": 2},
        "container_policy": {"immutable_digest_only": True, "pull_never_for_every_container_run": True, "offline_network_none": True, "read_only_root": True, "tmpfs_only_scratch": True, "non_root_uid_gid": "10001:10001", "capabilities_dropped": "ALL", "no_new_privileges": True, "pids_limit": 256, "cpus": 2, "memory": "4g", "repository_root_mounted": False, "whole_E_drive_mounted": False, "user_profile_mounted": False, "docker_socket_mounted": False},
        "allowed_mounts": [{"host":DATA_ROOT,"container":"/stage1e/data","mode":"rw attempt root only"},{"host":ENV_ROOT,"container":"/stage1e/env","mode":"rw attempt root only"},{"host":SOURCE_ROOT,"container":"/stage1e/recbole-source","mode":"ro exact verified source only"}],
        "typed_postcondition_adapters": adapters,
        "runner_preflight": {"must_be_implemented_and_independently_audited_before_execution": True, "checks": ["authoritative Git HEAD and clean worktree","G1 receipt raw hash","Docker executable regular non-reparse bytes and SHA-256","Docker/WSL stopped baseline","attempt roots absent and non-reparse ancestors","C free >=20 GiB and E free >=50 GiB","265/265 RecBole source files replay against Git-blob manifest","exact command argv hashes","fresh explicit user authorization"], "root_creation_occurs_only_after_I02_pass": True, "append_only_command_journal_fsync_after_each_command": True, "retry_or_fallback_count": 0, "finally_stop_docker_and_shutdown_wsl": True},
        "authorization_boundary": {"packet_design_authorized": True, "static_validation_authorized": True, "independent_audit_required": True, "image_pull_build_or_run_authorized": False, "materialization_authorized": False, "training_or_evaluation_authorized": False, "test_access_authorized": False},
        "negative_assertions": {"scientific_execution": False, "preprocessing_except_canonical_dataset_format_conversion": False, "training": False, "evaluation": False, "metric_calculation": False, "checkpoint_or_result_asset_retrieval": False, "test_access": False, "benchmark_admission": False, "paper_number_generation": False, "automatic_retry_cleanup_rollback_or_fallback": False},
        "truth_state": TRUTH_STATE,
    }

    handoff_doc = {
        "schema_version": "stage1e-r6-c1r3-linux-audit-handoff-1.0",
        "created_at": CREATED_AT,
        "stage_id": STAGE_ID,
        "artifact": "R6-C1R3-LINUX packet and typed postcondition adapter proposal",
        "material_passport": passport("stage1e_e4_r6_c1r3_linux_audit_handoff_v1", upstream),
        "proposal_only": True,
        "execution_performed": False,
        "execution_authorized": False,
        "entry": {"commit": "a939692d72d5d33cf67a8762d5260f2378df64f6", "g1_receipt": boundary_doc["g1_receipt"]},
        "actual_central_profile": {"model": "gpt-5.6-sol", "reasoning_effort": "max", "requested_service_tier": "default", "display_tier": "Standard", "actual_service_tier": "UNOBSERVABLE", "fast_or_priority_observed": False},
        "required_fresh_audit_profile": {"model": "gpt-5.6-sol", "reasoning_effort": "xhigh", "service_tier": "default", "display_tier": "Standard", "fast_or_priority_forbidden": True},
        "exact_output_set": PACKET_FILES,
        "command_counts": boundary_doc["command_counts"],
        "critical_audit_questions": ["Does the immutable manifest reference bind the exact official linux/amd64 image and forbid all tag fallback?","Do all container runs carry pull-never, read-only root, non-root, no-new-privileges, dropped capabilities, resource limits and correct network mode?","Are the only mounts exact source/data roots and one attempt root, with no repository/E-drive/profile/socket exposure?","Does GroupLens conversion preserve 100000 rows without filtering, sorting or ID rewrite?","Is the third-party closure wheel-only/hash-locked and is RecBole built non-editably from the 265-file source lock?","Can any command construct/load a dataset, train, evaluate, calculate metrics, open TEST or admit a benchmark row?","Are typed postcondition adapters sufficient to reject partial, wrong-platform, wrong-version, wrong-attempt or cross-lane evidence?"],
        "known_residuals": ["The historical Python image has registry-reported vulnerability metadata and is admitted only under the trusted-pinned-code threat model.","Transitive wheel identities and hashes become immutable only after the single authorized acquisition; any resolution failure closes the attempt.","The future central runner and exact process invocation are not part of this packet and require separate construction, audit and authorization."],
        "verdict": "PROPOSAL_R6_C1R3_LINUX_READY_FOR_CENTRAL_STATIC_VALIDATION_THEN_FRESH_XHIGH_AUDIT",
        "truth_state": TRUTH_STATE,
    }

    return {
        PACKET_FILES[0]: dataset_doc,
        PACKET_FILES[1]: environment_doc,
        PACKET_FILES[2]: bridge_doc,
        PACKET_FILES[3]: boundary_doc,
        PACKET_FILES[4]: handoff_doc,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    if output_root.exists() and any(output_root.iterdir()):
        observed = sorted(path.name for path in output_root.iterdir())
        if observed != sorted(PACKET_FILES) or not all(path.is_file() for path in output_root.iterdir()):
            raise SystemExit("OUTPUT_ROOT_NOT_EXACT_REPLACEABLE_PACKET")
    output_root.mkdir(parents=True, exist_ok=True)
    documents = make_documents()
    for name in PACKET_FILES:
        payload = json.dumps(documents[name], indent=2, ensure_ascii=False, sort_keys=False) + "\n"
        (output_root / name).write_text(payload, encoding="utf-8", newline="\n")
    observed = sorted(path.name for path in output_root.iterdir())
    if observed != sorted(PACKET_FILES):
        raise SystemExit("EXACT_OUTPUT_SET_FAILURE")
    print(json.dumps({"output_root": str(output_root), "files": observed, "verdict": "PACKET_GENERATED_NO_EXECUTION"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
