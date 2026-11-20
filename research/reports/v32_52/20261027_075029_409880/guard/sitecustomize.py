
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
    host = address[0] if isinstance(address, tuple) and address else address
    if not _is_loopback_host(host):
        raise RuntimeError("BTC_QA_NETWORK_BLOCKED: connect " + str(address))
    return _real_connect(self, address)
socket.socket.connect = _guarded_connect

_real_connect_ex = socket.socket.connect_ex
def _guarded_connect_ex(self, address):
    if self.family == getattr(socket, "AF_UNIX", object()):
        return _real_connect_ex(self, address)
    host = address[0] if isinstance(address, tuple) and address else address
    if not _is_loopback_host(host):
        raise RuntimeError("BTC_QA_NETWORK_BLOCKED: connect_ex " + str(address))
    return _real_connect_ex(self, address)
socket.socket.connect_ex = _guarded_connect_ex

_real_bind = socket.socket.bind
def _guarded_bind(self, address):
    if self.family != getattr(socket, "AF_UNIX", object()):
        host = address[0] if isinstance(address, tuple) and address else address
        if not _is_loopback_host(host):
            raise RuntimeError("BTC_QA_BIND_BLOCKED: bind " + str(address))
    return _real_bind(self, address)
socket.socket.bind = _guarded_bind

_real_popen = subprocess.Popen
def _guarded_popen(args, *call_args, **kwargs):
    if kwargs.get("shell", False):
        raise RuntimeError("BTC_QA_SUBPROCESS_BLOCKED: shell execution")
    executable = args[0] if isinstance(args, (list, tuple)) and args else args
    try:
        resolved = os.path.normcase(os.path.realpath(os.path.abspath(os.fsdecode(os.fspath(executable)))))
    except (TypeError, ValueError):
        resolved = ""
    expected = os.path.normcase(os.path.realpath(sys.executable))
    if resolved != expected:
        raise RuntimeError("BTC_QA_SUBPROCESS_BLOCKED: only the active Python interpreter is allowed")
    return _real_popen(args, *call_args, **kwargs)
subprocess.Popen = _guarded_popen

def _blocked_shell(*args, **kwargs):
    raise RuntimeError("BTC_QA_SUBPROCESS_BLOCKED: shell execution")
os.system = _blocked_shell
os.popen = _blocked_shell
