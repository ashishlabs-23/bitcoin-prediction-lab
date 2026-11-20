"""Prepare and run serial pytest groups in a disposable repository copy."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any

from v32_55_qa_fixtures import FIXTURE_ID, assert_fixture_bundle, build_fixture_bundle


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROTECTED_RELATIVE_PATHS = (
    Path("data/prospective_entry_ledger.jsonl"),
    Path("data/prospective_shadow_v1.jsonl"),
    Path("data/prospective_entry_ledger_v2.jsonl"),
    Path("data/raw/ohlcv.parquet"),
    Path("data/raw/ohlcv_pre_backfill_backup.parquet"),
    Path("data/raw/ohlcv_backfilled.parquet"),
)
IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".pytest_cache",
    ".venv",
    ".venv_win",
    "__pycache__",
    "node_modules",
    "venv",
}
IGNORED_ROOT_DIRECTORY_NAMES = {"scratch"}
IGNORED_FILE_NAMES = {".env", ".env.local", ".env.production"}


SITE_CUSTOMIZE_SOURCE = r'''
import builtins
import io
import ipaddress
import json
import os
import shutil
import socket
import subprocess
import sys

_protected = {
    os.path.normcase(os.path.realpath(os.path.abspath(os.fsdecode(path))))
    for path in json.loads(os.environ["BTC_QA_PROTECTED_PATHS"])
}
_port_ledger = os.environ["BTC_QA_PORT_LEDGER"]

def _qa_owned_ports():
    try:
        with _real_builtin_open(_port_ledger, "r", encoding="utf-8") as source:
            owners = set()
            for line in source:
                if not line.strip():
                    continue
                event = json.loads(line)
                key = (int(event["pid"]), int(event["port"]))
                if event["action"] == "bind":
                    owners.add(key)
                elif event["action"] == "close":
                    owners.discard(key)
            return {port for _, port in owners}
    except FileNotFoundError:
        return set()

def _record_qa_port(port, action):
    with _real_builtin_open(_port_ledger, "a", encoding="utf-8") as target:
        target.write(json.dumps({"action": action, "pid": os.getpid(), "port": int(port)}) + "\n")

def _record_network_event(action, address, allowed, ports):
    log_path = os.path.join(os.path.dirname(_port_ledger), "qa_network.jsonl")
    event = {
        "action": action,
        "address": str(address),
        "allowed": bool(allowed),
        "owned_ports": sorted(ports),
        "pid": os.getpid(),
    }
    with _real_builtin_open(log_path, "a", encoding="utf-8") as target:
        target.write(json.dumps(event) + "\n")

def _assert_qa_owned_loopback(address, operation):
    host = address[0] if isinstance(address, tuple) and address else address
    port = address[1] if isinstance(address, tuple) and len(address) > 1 else None
    ports = _qa_owned_ports()
    allowed = _is_loopback_host(host) and port in ports
    _record_network_event(operation, address, allowed, ports)
    if not allowed:
        raise RuntimeError("BTC_QA_NETWORK_BLOCKED: " + operation + " " + str(address))

def _normalized(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(os.fsdecode(os.fspath(path)))))

def _is_protected(path, include_parent=False):
    try:
        candidate = _normalized(path)
    except (TypeError, ValueError):
        return False
    if candidate in _protected:
        return True
    if include_parent:
        for item in _protected:
            try:
                if os.path.commonpath((candidate, item)) == candidate:
                    return True
            except ValueError:
                continue
    return False

def _deny(path, operation, include_parent=False):
    if _is_protected(path, include_parent):
        raise RuntimeError("BTC_QA_WRITE_BLOCKED: " + operation + " " + os.fsdecode(os.fspath(path)))

_real_builtin_open = builtins.open
def _guarded_builtin_open(file, mode="r", *args, **kwargs):
    if any(flag in mode for flag in "wxa+"):
        _deny(file, "open")
    return _real_builtin_open(file, mode, *args, **kwargs)
builtins.open = _guarded_builtin_open

_real_io_open = io.open
def _guarded_io_open(file, mode="r", *args, **kwargs):
    if any(flag in mode for flag in "wxa+"):
        _deny(file, "io.open")
    return _real_io_open(file, mode, *args, **kwargs)
io.open = _guarded_io_open

_real_os_open = os.open
_write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
def _guarded_os_open(path, flags, *args, **kwargs):
    if flags & _write_flags:
        _deny(path, "os.open")
    return _real_os_open(path, flags, *args, **kwargs)
os.open = _guarded_os_open

def _wrap_path_mutator(name, path_positions, include_parent=False, deny_dir_fd=False):
    original = getattr(os, name)
    def guarded(*args, **kwargs):
        if deny_dir_fd and any(kwargs.get(key) is not None for key in ("dir_fd", "src_dir_fd", "dst_dir_fd")):
            raise RuntimeError("BTC_QA_WRITE_BLOCKED: " + name + " with dir_fd")
        for position in path_positions:
            if position < len(args):
                _deny(args[position], name, include_parent)
        return original(*args, **kwargs)
    setattr(os, name, guarded)

for _name, _positions, _parents, _dir_fd in (
    ("remove", (0,), True, True),
    ("unlink", (0,), True, True),
    ("rmdir", (0,), True, True),
    ("rename", (0, 1), True, True),
    ("replace", (0, 1), True, True),
    ("truncate", (0,), False, False),
    ("chmod", (0,), False, False),
    ("utime", (0,), False, False),
    ("chown", (0,), False, False),
    ("link", (0, 1), True, True),
    ("symlink", (1,), True, False),
):
    if hasattr(os, _name):
        _wrap_path_mutator(_name, _positions, _parents, _dir_fd)

_real_copyfile = shutil.copyfile
def _guarded_copyfile(src, dst, *args, **kwargs):
    _deny(dst, "shutil.copyfile", include_parent=True)
    return _real_copyfile(src, dst, *args, **kwargs)
shutil.copyfile = _guarded_copyfile

_real_copy = shutil.copy
def _guarded_copy(src, dst, *args, **kwargs):
    _deny(dst, "shutil.copy", include_parent=True)
    return _real_copy(src, dst, *args, **kwargs)
shutil.copy = _guarded_copy

_real_copy2 = shutil.copy2
def _guarded_copy2(src, dst, *args, **kwargs):
    _deny(dst, "shutil.copy2", include_parent=True)
    return _real_copy2(src, dst, *args, **kwargs)
shutil.copy2 = _guarded_copy2

_real_move = shutil.move
def _guarded_move(src, dst, *args, **kwargs):
    _deny(src, "shutil.move", include_parent=True)
    _deny(dst, "shutil.move", include_parent=True)
    return _real_move(src, dst, *args, **kwargs)
shutil.move = _guarded_move

_real_rmtree = shutil.rmtree
def _guarded_rmtree(path, *args, **kwargs):
    _deny(path, "shutil.rmtree", include_parent=True)
    return _real_rmtree(path, *args, **kwargs)
shutil.rmtree = _guarded_rmtree

_real_copytree = shutil.copytree
def _guarded_copytree(src, dst, *args, **kwargs):
    _deny(dst, "shutil.copytree", include_parent=True)
    return _real_copytree(src, dst, *args, **kwargs)
shutil.copytree = _guarded_copytree

def _is_loopback_host(host):
    if host is None or str(host).lower() == "localhost":
        return host is not None
    try:
        return ipaddress.ip_address(str(host).split("%", 1)[0]).is_loopback
    except ValueError:
        return False

_real_getaddrinfo = socket.getaddrinfo
def _guarded_getaddrinfo(host, *args, **kwargs):
    if host is not None and not _is_loopback_host(host):
        raise RuntimeError("BTC_QA_NETWORK_BLOCKED: DNS/address lookup " + str(host))
    return _real_getaddrinfo(host, *args, **kwargs)
socket.getaddrinfo = _guarded_getaddrinfo

_real_connect = socket.socket.connect
def _guarded_connect(self, address):
    if self.family == getattr(socket, "AF_UNIX", object()):
        return _real_connect(self, address)
    _assert_qa_owned_loopback(address, "connect")
    return _real_connect(self, address)
socket.socket.connect = _guarded_connect

_real_connect_ex = socket.socket.connect_ex
def _guarded_connect_ex(self, address):
    if self.family == getattr(socket, "AF_UNIX", object()):
        return _real_connect_ex(self, address)
    _assert_qa_owned_loopback(address, "connect_ex")
    return _real_connect_ex(self, address)
socket.socket.connect_ex = _guarded_connect_ex

_real_bind = socket.socket.bind
_owned_socket_ports = {}
def _guarded_bind(self, address):
    if self.family != getattr(socket, "AF_UNIX", object()):
        host = address[0] if isinstance(address, tuple) and address else address
        if not _is_loopback_host(host):
            raise RuntimeError("BTC_QA_BIND_BLOCKED: bind " + str(address))
    result = _real_bind(self, address)
    if self.family != getattr(socket, "AF_UNIX", object()):
        try:
            port = int(self.getsockname()[1])
            _record_qa_port(port, "bind")
            _owned_socket_ports[id(self)] = port
        except (OSError, TypeError, ValueError) as exc:
            self.close()
            raise RuntimeError("BTC_QA_PORT_LEDGER_ERROR: failed to record bound QA port") from exc
    return result
socket.socket.bind = _guarded_bind

_real_close = socket.socket.close
def _guarded_close(self):
    port = _owned_socket_ports.pop(id(self), None)
    result = _real_close(self)
    if port is not None:
        _record_qa_port(port, "close")
    return result
socket.socket.close = _guarded_close

_real_sendto = socket.socket.sendto
def _guarded_sendto(self, data, *args):
    address = args[-1] if args and isinstance(args[-1], tuple) else None
    if address is None:
        raise RuntimeError("BTC_QA_NETWORK_BLOCKED: sendto without a verifiable destination")
    _assert_qa_owned_loopback(address, "sendto")
    return _real_sendto(self, data, *args)
socket.socket.sendto = _guarded_sendto

_real_popen = subprocess.Popen
def _assert_allowed_process(args, kwargs):
    command = args[0] if isinstance(args, (list, tuple)) and args else args
    if (
        kwargs.get("shell", False)
        and sys.platform == "win32"
        and isinstance(command, str)
        and command.strip().lower() == "ver"
    ):
        return
    if kwargs.get("shell", False):
        raise RuntimeError("BTC_QA_SUBPROCESS_BLOCKED: shell execution")
    requested_executable = kwargs.get("executable")
    executable = requested_executable or (args[0] if isinstance(args, (list, tuple)) and args else args)
    try:
        executable_text = os.fsdecode(os.fspath(executable))
        executable_path = (
            executable_text
            if os.path.dirname(executable_text)
            else shutil.which(executable_text) or executable_text
        )
        resolved = os.path.normcase(os.path.realpath(os.path.abspath(executable_path)))
    except (TypeError, ValueError):
        resolved = ""
    expected = os.path.normcase(os.path.realpath(sys.executable))
    if resolved == expected and not requested_executable:
        return

    node_name = os.path.basename(os.fsdecode(os.fspath(executable))).lower()
    node_path = shutil.which("node")
    command = [os.fsdecode(os.fspath(item)) for item in args] if isinstance(args, (list, tuple)) else []
    working_directory = os.path.realpath(kwargs.get("cwd") or os.getcwd())
    sandbox_root = os.path.realpath(os.environ["BTC_QA_SANDBOX_ROOT"])
    if (
        node_name in {"node", "node.exe"}
        and node_path
        and not requested_executable
        and resolved == os.path.normcase(os.path.realpath(node_path))
        and working_directory == sandbox_root
        and command == [command[0], "build_frontend.js"]
    ):
        return
    raise RuntimeError("BTC_QA_SUBPROCESS_BLOCKED: only Python or the sandbox frontend smoke build is allowed")

class _GuardedPopen(_real_popen):
    def __init__(self, args, *call_args, **kwargs):
        _assert_allowed_process(args, kwargs)
        super().__init__(args, *call_args, **kwargs)

subprocess.Popen = _GuardedPopen

def _blocked_shell(*args, **kwargs):
    raise RuntimeError("BTC_QA_SUBPROCESS_BLOCKED: shell execution")
os.system = _blocked_shell
os.popen = _blocked_shell
for _name in dir(os):
    if _name.startswith(("spawn", "exec")) or _name == "startfile":
        setattr(os, _name, _blocked_shell)
'''


def _protected_paths(root: Path = REPOSITORY_ROOT) -> list[Path]:
    paths = [root / relative for relative in PROTECTED_RELATIVE_PATHS]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Protected files missing: " + ", ".join(missing))
    return paths


def _file_facts(paths: list[Path]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in paths:
        stat = path.stat()
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        result[str(path)] = {
            "sha256": digest.hexdigest(),
            "size_bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        }
    return result


def _assert_unchanged(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> None:
    changed = [
        path
        for path, facts in before.items()
        if after.get(path) != facts
    ]
    if changed:
        raise RuntimeError(
            "Protected-file integrity check failed; no recovery was attempted: "
            + ", ".join(changed)
        )


def _source_absolute_path_references(root: Path) -> list[str]:
    needles = {
        os.path.normcase(str(root.resolve())),
        os.path.normcase(str(root.resolve()).replace("\\", "/")),
    }
    found: list[str] = []
    for directory, dirnames, filenames in os.walk(root):
        is_repository_root = Path(directory).resolve() == root.resolve()
        dirnames[:] = [
            name for name in dirnames
            if name not in IGNORED_DIRECTORY_NAMES
            and not (is_repository_root and name in IGNORED_ROOT_DIRECTORY_NAMES)
            and not (Path(directory) / name).is_symlink()
        ]
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            path = Path(directory) / filename
            try:
                content = path.read_text(encoding="utf-8", errors="replace").casefold()
            except OSError as exc:
                raise RuntimeError(f"Unable to scan source path {path}: {exc}") from exc
            if any(needle.casefold() in content for needle in needles):
                found.append(str(path.relative_to(root)))
    return found


def _ignore_copy(directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    is_repository_root = Path(directory).resolve() == REPOSITORY_ROOT.resolve()
    for name in names:
        path = Path(directory) / name
        if (
            path.is_symlink()
            or name in IGNORED_DIRECTORY_NAMES
            or (is_repository_root and name in IGNORED_ROOT_DIRECTORY_NAMES)
            or name in IGNORED_FILE_NAMES
            or name.startswith(".env")
            or name.lower().endswith((".pem", ".key", ".p12", ".pfx"))
        ):
            ignored.add(name)
    return ignored


def _make_report_directory() -> Path:
    run_id = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report_dir = REPOSITORY_ROOT / "research" / "reports" / "v32_55" / run_id
    report_dir.mkdir(parents=True, exist_ok=False)
    return report_dir


def _make_sandbox() -> tuple[Path, Path]:
    parent = Path(tempfile.mkdtemp(prefix="btcognitive_v32_52_"))
    sandbox = parent / "repository"
    shutil.copytree(REPOSITORY_ROOT, sandbox, ignore=_ignore_copy, symlinks=False)
    return parent, sandbox


def _clean_environment(
    run_dir: Path,
    guard_dir: Path,
    sandbox: Path,
    protected: list[Path],
    dataset: Path | None,
    dataset_mode: str | None,
    fixture_id: str | None,
) -> dict[str, str]:
    env = {
        key: os.environ[key]
        for key in ("PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT")
        if key in os.environ
    }
    temp_dir = run_dir / "tmp"
    home_dir = run_dir / "home"
    temp_dir.mkdir(parents=True, exist_ok=True)
    home_dir.mkdir(parents=True, exist_ok=True)
    env.update({
        "APPDATA": str(home_dir),
        "BTC_ENVIRONMENT": "test",
        "BTC_QA_PROTECTED_PATHS": json.dumps([str(path) for path in protected]),
        "BTC_QA_PORT_LEDGER": str(run_dir / "qa_owned_ports.jsonl"),
        "BTC_QA_SANDBOX_ROOT": str(sandbox),
        "BTC_QA_RUN_DIR": str(run_dir),
        "HOME": str(home_dir),
        "LOCALAPPDATA": str(home_dir),
        "NO_PROXY": "*",
        "no_proxy": "*",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(guard_dir) + os.pathsep + str(sandbox),
        "SQLITE_DB_PATH": str(run_dir / "state" / "market_memory.db"),
        "TEMP": str(temp_dir),
        "TMP": str(temp_dir),
        "USERPROFILE": str(home_dir),
    })
    if dataset is not None and dataset_mode == "VERIFIED_DATASET":
        env["BTC_QA_VERIFIED_DATASET"] = str(dataset)
        env["BTC_QA_VERIFIED_DATASET_SHA256"] = hashlib.sha256(dataset.read_bytes()).hexdigest()
    if dataset is not None and dataset_mode == "QA_FIXTURE":
        env["BTC_QA_DATASET_MODE"] = "QA_FIXTURE"
        env["BTC_QA_FIXTURE_ID"] = fixture_id or "unknown"
        env["BTC_QA_FIXTURE_SHA256"] = hashlib.sha256(dataset.read_bytes()).hexdigest()
    return env


def _write_manifest(report_dir: Path, manifest: dict[str, Any]) -> None:
    target = report_dir / "manifest.json"
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _self_test_guard() -> None:
    with tempfile.TemporaryDirectory(prefix="btcognitive_v32_52_guard_test_") as temporary:
        root = Path(temporary)
        protected = root / "sentinel.bin"
        move_source = root / "move_source.bin"
        protected.write_bytes(b"guard-sentinel")
        move_source.write_bytes(b"move-source")
        before_protected = hashlib.sha256(protected.read_bytes()).hexdigest()
        before_source = hashlib.sha256(move_source.read_bytes()).hexdigest()
        guard_dir = root / "guard"
        guard_dir.mkdir()
        (guard_dir / "sitecustomize.py").write_text(SITE_CUSTOMIZE_SOURCE, encoding="utf-8")
        env = {
            key: os.environ[key]
            for key in ("PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT")
            if key in os.environ
        }
        env["BTC_QA_PROTECTED_PATHS"] = json.dumps([str(protected)])
        env["BTC_QA_PORT_LEDGER"] = str(root / "owned_ports.jsonl")
        env["BTC_QA_SANDBOX_ROOT"] = str(root)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(guard_dir)
        checks = (
            (
                "write",
                "from pathlib import Path; import sys; Path(sys.argv[1]).write_bytes(b'changed')",
                str(protected),
            ),
            (
                "replace",
                "import os, sys; os.replace(sys.argv[1], sys.argv[2])",
                str(move_source),
                str(protected),
            ),
            (
                "external DNS",
                "import socket; socket.getaddrinfo('example.invalid', 443)",
            ),
            (
                "external connect",
                "import socket; socket.create_connection(('203.0.113.1', 443), timeout=0.1)",
            ),
            (
                "unowned loopback connect",
                "import socket; socket.create_connection(('127.0.0.1', 9), timeout=0.1)",
            ),
            (
                "external process",
                "import subprocess; subprocess.run(['cmd.exe', '/c', 'echo unsafe'], check=False)",
            ),
        )
        for name, code, *arguments in checks:
            completed = subprocess.run(
                [sys.executable, "-B", "-c", code, *arguments],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            marker = "BTC_QA_WRITE_BLOCKED" if name in {"write", "replace"} else (
                "BTC_QA_NETWORK_BLOCKED" if name in {"external DNS", "external connect", "unowned loopback connect"}
                else "BTC_QA_SUBPROCESS_BLOCKED"
            )
            if completed.returncode == 0 or marker not in completed.stderr:
                raise RuntimeError(f"Guard self-test failed for {name}: {completed.stderr}")
        allowed_child = subprocess.run(
            [sys.executable, "-B", "-c", "print('isolated child')"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if allowed_child.returncode != 0 or "isolated child" not in allowed_child.stdout:
            raise RuntimeError(f"Guard self-test failed for active Python child: {allowed_child.stderr}")
        allowed_loopback = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                "import socket; s=socket.socket(); s.bind(('127.0.0.1', 0)); s.listen(1); c=socket.create_connection(s.getsockname(), timeout=1); accepted, _=s.accept(); accepted.close(); c.close(); s.close()",
            ],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if allowed_loopback.returncode != 0:
            raise RuntimeError(f"Guard self-test failed for QA-owned loopback socket: {allowed_loopback.stderr}")
        node_path = shutil.which("node")
        if not node_path:
            raise RuntimeError("Node.js is required to validate the sandbox frontend smoke-test exception")
        (root / "build_frontend.js").write_text(
            "console.log('isolated node child')\n",
            encoding="utf-8",
        )
        allowed_node = subprocess.run(
            [node_path, "build_frontend.js"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if allowed_node.returncode != 0 or "isolated node child" not in allowed_node.stdout:
            raise RuntimeError(f"Guard self-test failed for sandbox Node build: {allowed_node.stderr}")
        if hashlib.sha256(protected.read_bytes()).hexdigest() != before_protected:
            raise RuntimeError("Guard self-test changed its disposable protected sentinel")
        if hashlib.sha256(move_source.read_bytes()).hexdigest() != before_source:
            raise RuntimeError("Guard self-test changed its disposable move source")
    print(
        "GUARD_SELF_TEST_PASS: protected writes/replacements, external and unowned loopback "
        "connections, and non-Python processes blocked; QA-owned loopback and Python child allowed"
    )


def _prepare_or_run(args: argparse.Namespace) -> int:
    protected = _protected_paths()
    before = _file_facts(protected)
    if args.run and args.verified_dataset is None and args.qa_fixture is None:
        raise ValueError("--run requires exactly one explicitly named dataset source")
    verified_source = args.verified_dataset.resolve() if args.verified_dataset else None
    verified_hash = None
    dataset_status = None
    dataset_mode = "VERIFIED_DATASET" if verified_source is not None else ("QA_FIXTURE" if args.qa_fixture else None)
    if verified_source is not None:
        if not verified_source.is_file():
            raise FileNotFoundError(f"Verified QA dataset not found: {verified_source}")
        verified_hash = hashlib.sha256(verified_source.read_bytes()).hexdigest()
        dataset_manifest_path = verified_source.parent / "acquisition_manifest.json"
        if not dataset_manifest_path.is_file():
            raise FileNotFoundError(
                f"Acquisition manifest not found beside verified dataset: {dataset_manifest_path}"
            )
        dataset_manifest = json.loads(dataset_manifest_path.read_text(encoding="utf-8"))
        if dataset_manifest.get("dataset_sha256") != verified_hash:
            raise RuntimeError("Verified QA dataset hash differs from its manifest")
        if dataset_manifest.get("dataset_id") != "coinbase_btc_usd_hourly_verified_v2":
            raise RuntimeError("QA dataset is not the V32.54 verified dataset version")
        dataset_status = dataset_manifest.get("status")
        if dataset_status == "ACQUIRED_WITH_REVIEW_REQUIRED" and not args.allow_review_required_dataset:
            raise RuntimeError(
                "Dataset has unresolved validation findings; exploratory QA requires "
                "--allow-review-required-dataset"
            )
        if dataset_status not in {
            "ACQUIRED_VALIDATION_PASSED",
            "ACQUIRED_WITH_REVIEW_REQUIRED",
        }:
            raise RuntimeError(
                "Unsupported dataset acquisition status: "
                f"{dataset_status}"
            )
    absolute_references = _source_absolute_path_references(REPOSITORY_ROOT)
    if absolute_references:
        raise RuntimeError(
            "Hard-coded workspace-root reference requires review before isolated tests: "
            + ", ".join(absolute_references)
        )

    report_dir = _make_report_directory()
    run_parent, sandbox = _make_sandbox()
    guard_dir = report_dir / "guard"
    guard_dir.mkdir()
    (guard_dir / "sitecustomize.py").write_text(SITE_CUSTOMIZE_SOURCE, encoding="utf-8")
    sandbox_dataset = None
    fixture_bundle = None
    if verified_source is not None:
        sandbox_dataset = sandbox / "data" / "raw" / "ohlcv.parquet"
        shutil.copy2(verified_source, sandbox_dataset)
        if hashlib.sha256(sandbox_dataset.read_bytes()).hexdigest() != verified_hash:
            raise RuntimeError("Sandbox dataset copy failed its SHA-256 check")
    elif args.qa_fixture:
        if args.qa_fixture != FIXTURE_ID:
            raise ValueError(f"Unsupported QA fixture: {args.qa_fixture}")
        fixture_bundle = build_fixture_bundle(sandbox)
        assert_fixture_bundle(fixture_bundle, sandbox)
        sandbox_dataset = sandbox / "data" / "raw" / "ohlcv.parquet"
        shutil.copy2(fixture_bundle["fixtures"]["normal_hourly"]["path"], sandbox_dataset)
        verified_hash = hashlib.sha256(sandbox_dataset.read_bytes()).hexdigest()
    env = _clean_environment(
        report_dir, guard_dir, sandbox, protected, sandbox_dataset, dataset_mode, args.qa_fixture
    )

    manifest: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "run" if args.run else "prepare_only",
        "repository_root": str(REPOSITORY_ROOT),
        "branch": _git_output("branch", "--show-current"),
        "head": _git_output("rev-parse", "HEAD"),
        "report_directory": str(report_dir),
        "sandbox_parent": str(run_parent),
        "sandbox_root": str(sandbox),
        "source_absolute_path_references": absolute_references,
        "verified_dataset_source": str(verified_source) if verified_source else None,
        "verified_dataset_sha256": verified_hash,
        "verified_dataset_acquisition_status": dataset_status,
        "dataset_mode": dataset_mode,
        "qa_fixture_id": args.qa_fixture,
        "qa_fixture_manifest": fixture_bundle["manifest_path"] if fixture_bundle else None,
        "qa_fixture_provenance": ({"qa_only": True, "not_market_evidence": True, "not_forecast_source": True} if fixture_bundle else None),
        "review_required_dataset_override": bool(
            dataset_status == "ACQUIRED_WITH_REVIEW_REQUIRED"
            and args.allow_review_required_dataset
        ),
        "sandbox_dataset_override": (
            str(sandbox_dataset.relative_to(sandbox))
            if sandbox_dataset is not None
            else None
        ),
        "sandbox_dataset_override_sha256": verified_hash,
        "excluded_root_directories": {
            "scratch": "Contains ad hoc scripts with absolute workspace paths; no references from code, tests, or configuration were found.",
        },
        "protected_files_before": before,
        "protected_files_after": None,
        "protected_files_unchanged": None,
        "network_policy": "only loopback ports bound by this QA run are reachable; external DNS and connections are blocked",
        "python_guard": "sitecustomize blocks write, replace, delete, copy, move, metadata changes, and removal of protected paths",
        "subprocess_policy": "Python children and the sandbox frontend smoke build are allowed; only the exact Windows 'ver' platform probe may use a shell",
        "pytest_command": None,
        "pytest_exit_code": None,
        "tests_executed": False,
        "network_log": str(report_dir / "qa_network.jsonl"),
        "limitations": [
            "The repository copy is the isolation boundary; this is not a kernel-level sandbox.",
            "Native extensions or non-Python child processes are not intercepted by sitecustomize.",
            "Protected-file before/after comparison detects unexpected changes but does not restore them.",
        ],
    }

    try:
        if args.run:
            if any(
                item == "-n"
                or item.startswith("--numprocesses")
                or item.startswith("-n=")
                for item in args.pytest_args
            ):
                raise ValueError("Parallel pytest workers are forbidden; run one serial group at a time")
            python = _pytest_python()
            pytest_args = args.pytest_args or ["tests"]
            command = [str(python), "-B", "-m", "pytest", *pytest_args]
            manifest["pytest_command"] = command
            completed = subprocess.run(
                command,
                cwd=sandbox,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            manifest["pytest_exit_code"] = completed.returncode
            manifest["tests_executed"] = True
            (report_dir / "pytest.log").write_text(completed.stdout, encoding="utf-8")
        else:
            manifest["prepare_only_note"] = "No pytest command was executed."
    finally:
        after = _file_facts(protected)
        _assert_unchanged(before, after)
        manifest["protected_files_after"] = after
        manifest["protected_files_unchanged"] = True
        _write_manifest(report_dir, manifest)

    print(f"REPORT_DIR={report_dir}")
    print(f"DISPOSABLE_SANDBOX={sandbox}")
    print("PROTECTED_HASH_CHECK=UNCHANGED")
    if args.run:
        print(f"PYTEST_EXIT_CODE={manifest['pytest_exit_code']}")
        return int(manifest["pytest_exit_code"])
    print("PYTEST=NOT_RUN")
    return 0


def _pytest_python() -> Path:
    candidates = (
        REPOSITORY_ROOT / ".venv_win" / "Scripts" / "python.exe",
        Path(sys.executable),
    )
    for candidate in candidates:
        if candidate.is_file():
            check = subprocess.run(
                [str(candidate), "-B", "-c", "import pytest"],
                cwd=REPOSITORY_ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if check.returncode == 0:
                return candidate
    raise RuntimeError("No available Python interpreter has pytest installed; no dependencies were installed")


def _git_output(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Use a disposable repository copy and protected-path guards for serial pytest."
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true", help="test write guards against disposable sentinels")
    modes.add_argument("--fixture-self-test", action="store_true", help="test deterministic QA-fixture containment")
    modes.add_argument("--prepare-only", action="store_true", help="prepare a sandbox; do not execute tests")
    modes.add_argument("--run", action="store_true", help="execute one serial pytest group in the sandbox")
    dataset_sources = parser.add_mutually_exclusive_group()
    dataset_sources.add_argument(
        "--verified-dataset",
        type=Path,
        help="V32.54 verified parquet copied only into the disposable sandbox.",
    )
    dataset_sources.add_argument("--qa-fixture", help=f"explicit QA-only fixture id; currently {FIXTURE_ID}")
    parser.add_argument(
        "--allow-review-required-dataset",
        action="store_true",
        help="allow exploratory isolated QA with ACQUIRED_WITH_REVIEW_REQUIRED data; records the override",
    )
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER, help="pytest selectors/options for --run")
    args = parser.parse_args()

    if args.self_test:
        _self_test_guard()
        return 0
    if args.fixture_self_test:
        with tempfile.TemporaryDirectory(prefix="btcognitive_v32_55_fixture_test_") as temporary:
            root = Path(temporary)
            first = build_fixture_bundle(root)
            assert_fixture_bundle(first, root)
            second = build_fixture_bundle(root / "second")
            if first["fixtures"]["normal_hourly"]["sha256"] != second["fixtures"]["normal_hourly"]["sha256"]:
                raise RuntimeError("Deterministic fixture hash changed between identical builds")
        print("FIXTURE_SELF_TEST_PASS: QA-only fixture matrix is deterministic and root-contained")
        return 0
    return _prepare_or_run(args)


if __name__ == "__main__":
    raise SystemExit(main())
