
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

def _assert_qa_owned_loopback(address, operation):
    host = address[0] if isinstance(address, tuple) and address else address
    port = address[1] if isinstance(address, tuple) and len(address) > 1 else None
    if not _is_loopback_host(host) or port not in _qa_owned_ports():
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
