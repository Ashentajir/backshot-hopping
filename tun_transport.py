"""Cross-platform TUN/TAP helpers for HopShot.

Linux uses /dev/net/tun directly.
Windows uses Wintun for a dependency-free TUN backend. TAP requests on Windows
are normalized to TUN because Wintun is layer-3 only.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import ipaddress
import os
import platform
import shlex
import struct
import subprocess
import warnings
from dataclasses import dataclass, replace
from typing import Optional

try:
    import fcntl
except Exception:  # pragma: no cover - unavailable on Windows
    fcntl = None

try:
    from ctypes import wintypes
except Exception:  # pragma: no cover - unavailable on non-Windows
    wintypes = None


TUNSETIFF = 0x400454ca
IFF_TUN = 0x0001
IFF_TAP = 0x0002
IFF_NO_PI = 0x1000

WINTUN_POOL = "HopShot"
WINTUN_SESSION_CAPACITY = 0x400000


class TunTapError(RuntimeError):
    pass


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _find_windows_wintun_dll() -> Optional[str]:
    if not _is_windows():
        return None

    candidates = []
    env_path = os.environ.get("WINTUN_DLL")
    if env_path:
        candidates.append(env_path)

    library_path = ctypes.util.find_library("wintun")
    if library_path:
        candidates.append(library_path)

    candidates.extend([
        r"C:\Program Files\Cloudflare\Cloudflare WARP\wintun.dll",
        r"C:\Program Files (x86)\Cloudflare\Cloudflare WARP\wintun.dll",
        os.path.join(os.getcwd(), "wintun.dll"),
    ])

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def _prefix_to_netmask(prefix_length: int) -> str:
    if prefix_length < 0 or prefix_length > 32:
        raise TunTapError(f"Invalid IPv4 prefix length: {prefix_length}")
    mask = (0xFFFFFFFF << (32 - prefix_length)) & 0xFFFFFFFF if prefix_length else 0
    return str(ipaddress.IPv4Address(mask))


def _run_powershell(script: str) -> None:
    command = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script]
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as e:
        raise TunTapError("PowerShell is required to configure Windows tunnel interfaces") from e
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace").strip()
        raise TunTapError(stderr or "PowerShell tunnel configuration failed") from e


def _load_wintun_library():
    dll_path = _find_windows_wintun_dll()
    if not dll_path:
        raise TunTapError("wintun.dll not found; install Wintun or Cloudflare WARP and retry")

    if wintypes is None:
        raise TunTapError("Windows ctypes bindings unavailable")

    lib = ctypes.WinDLL(dll_path, use_last_error=True)
    lib.WintunCreateAdapter.restype = wintypes.HANDLE
    lib.WintunCreateAdapter.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p]
    lib.WintunOpenAdapter.restype = wintypes.HANDLE
    lib.WintunOpenAdapter.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    lib.WintunCloseAdapter.restype = None
    lib.WintunCloseAdapter.argtypes = [wintypes.HANDLE]
    lib.WintunStartSession.restype = wintypes.HANDLE
    lib.WintunStartSession.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    lib.WintunEndSession.restype = None
    lib.WintunEndSession.argtypes = [wintypes.HANDLE]
    lib.WintunGetReadWaitEvent.restype = wintypes.HANDLE
    lib.WintunGetReadWaitEvent.argtypes = [wintypes.HANDLE]
    lib.WintunReceivePacket.restype = ctypes.POINTER(ctypes.c_ubyte)
    lib.WintunReceivePacket.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    lib.WintunReleaseReceivePacket.restype = None
    lib.WintunReleaseReceivePacket.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_ubyte)]
    lib.WintunAllocateSendPacket.restype = ctypes.POINTER(ctypes.c_ubyte)
    lib.WintunAllocateSendPacket.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    lib.WintunSendPacket.restype = None
    lib.WintunSendPacket.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_ubyte)]
    return lib


def is_supported() -> bool:
    if _is_windows():
        return _find_windows_wintun_dll() is not None
    return fcntl is not None and os.path.exists("/dev/net/tun")


@dataclass
class TunTapConfig:
    name: Optional[str] = None
    mode: str = "tun"
    mtu: int = 1500
    address: Optional[str] = None
    peer: Optional[str] = None
    up: bool = True
    route_default: bool = False


class WindowsTunTapDevice:
    def __init__(self, adapter, session, name: str, config: TunTapConfig, wintun_lib):
        self._adapter = adapter
        self._session = session
        self._name = name
        self._config = config
        self._wintun = wintun_lib
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._read_wait_event = self._wintun.WintunGetReadWaitEvent(self._session)
        self.backend = "wintun"
        self.name = name
        self.config = config

    @classmethod
    def open(cls, config: TunTapConfig) -> "WindowsTunTapDevice":
        if config.mode == "tap":
            warnings.warn("Windows Wintun backend is layer-3 only; mapping tap -> tun", RuntimeWarning)
            config = replace(config, mode="tun")
        if config.mode != "tun":
            raise TunTapError(f"Windows backend supports tun only (got {config.mode})")

        wintun_lib = _load_wintun_library()
        adapter_name = config.name or "hopshot0"
        adapter = wintun_lib.WintunOpenAdapter(WINTUN_POOL, adapter_name)
        if not adapter:
            adapter = wintun_lib.WintunCreateAdapter(WINTUN_POOL, adapter_name, None)
        if not adapter:
            raise TunTapError(f"Failed to open or create Wintun adapter '{adapter_name}'")

        session = wintun_lib.WintunStartSession(adapter, WINTUN_SESSION_CAPACITY)
        if not session:
            wintun_lib.WintunCloseAdapter(adapter)
            raise TunTapError("Failed to start Wintun session")

        device = cls(adapter, session, adapter_name, config, wintun_lib)
        device._configure_interface()
        return device

    def _configure_interface(self) -> None:
        if self._config.mtu > 0:
            script = f"Set-NetIPInterface -InterfaceAlias '{self._name}' -AddressFamily IPv4 -NlMtu {self._config.mtu} | Out-Null"
            _run_powershell(script)

        if self._config.address:
            interface = ipaddress.ip_interface(self._config.address)
            ip_address = str(interface.ip)
            prefix_length = interface.network.prefixlen
            gateway = self._config.peer
            if self._config.route_default and not gateway:
                raise TunTapError("Windows tunnel default route requires tunnel_peer to be set")

            command = [
                f"New-NetIPAddress -InterfaceAlias '{self._name}'",
                f"-IPAddress '{ip_address}'",
                f"-PrefixLength {prefix_length}",
            ]
            if gateway:
                command.append(f"-DefaultGateway '{gateway}'")
            command.append("| Out-Null")
            _run_powershell(" ".join(command))

            if self._config.route_default and gateway:
                route_script = (
                    f"New-NetRoute -DestinationPrefix '0.0.0.0/0' -InterfaceAlias '{self._name}' "
                    f"-NextHop '{gateway}' -RouteMetric 1 | Out-Null"
                )
                _run_powershell(route_script)

    def fileno(self) -> int:
        raise OSError("Windows Wintun device does not expose a file descriptor")

    def read(self, size: int = 65535) -> bytes:
        packet_size = wintypes.DWORD()
        while True:
            packet = self._wintun.WintunReceivePacket(self._session, ctypes.byref(packet_size))
            if packet:
                try:
                    return ctypes.string_at(packet, packet_size.value)
                finally:
                    self._wintun.WintunReleaseReceivePacket(self._session, packet)

            wait_result = self._kernel32.WaitForSingleObject(self._read_wait_event, 0xFFFFFFFF)
            if wait_result == 0xFFFFFFFF:
                raise TunTapError("WaitForSingleObject failed while reading Wintun packet")

    def write(self, data: bytes) -> int:
        if len(data) == 0:
            return 0
        packet = self._wintun.WintunAllocateSendPacket(self._session, len(data))
        if not packet:
            raise TunTapError("WintunAllocateSendPacket failed")
        ctypes.memmove(packet, data, len(data))
        self._wintun.WintunSendPacket(self._session, packet)
        return len(data)

    def close(self) -> None:
        if getattr(self, "_session", None):
            try:
                self._wintun.WintunEndSession(self._session)
            except Exception:
                pass
            self._session = None
        if getattr(self, "_adapter", None):
            try:
                self._wintun.WintunCloseAdapter(self._adapter)
            except Exception:
                pass
            self._adapter = None

    def __enter__(self) -> "WindowsTunTapDevice":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class TunTapDevice:
    def __init__(self, fd: int, name: str, config: TunTapConfig):
        self._fd = fd
        self.name = name
        self.config = config
        self.backend = "kernel"

    @classmethod
    def open(cls, config: TunTapConfig):
        if _is_windows():
            return WindowsTunTapDevice.open(config)

        if not is_supported():
            raise TunTapError("TUN/TAP is only supported on Unix-like systems with /dev/net/tun")
        if config.mode not in {"tun", "tap"}:
            raise TunTapError(f"Unsupported tunnel mode: {config.mode}")

        flags = IFF_NO_PI | (IFF_TUN if config.mode == "tun" else IFF_TAP)
        fd = os.open("/dev/net/tun", os.O_RDWR)
        ifr_name = (config.name or "").encode("utf-8")[:15]
        ifr = struct.pack("16sH", ifr_name, flags)
        try:
            res = fcntl.ioctl(fd, TUNSETIFF, ifr)
        except Exception as e:
            os.close(fd)
            raise TunTapError(f"Failed to create {config.mode}: {e}") from e

        name = res[:16].split(b"\x00", 1)[0].decode("utf-8") or (config.name or "tun0")
        device = cls(fd, name, config)
        device._configure_interface()
        return device

    def _run_ip(self, *args: str) -> None:
        command = ["ip", *args]
        try:
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FileNotFoundError as e:
            raise TunTapError("'ip' command not found; install iproute2 and try again") from e
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode("utf-8", errors="replace").strip()
            raise TunTapError(f"ip {' '.join(shlex.quote(a) for a in args)} failed: {stderr}") from e

    def _configure_interface(self) -> None:
        if self.config.mtu > 0:
            self._run_ip("link", "set", "dev", self.name, "mtu", str(self.config.mtu))

        if self.config.address:
            if self.config.peer:
                self._run_ip("addr", "add", self.config.address, "peer", self.config.peer, "dev", self.name)
            else:
                self._run_ip("addr", "add", self.config.address, "dev", self.name)

        if self.config.route_default:
            self._run_ip("route", "replace", "default", "dev", self.name)

        if self.config.up:
            self._run_ip("link", "set", "dev", self.name, "up")

    def fileno(self) -> int:
        return self._fd

    def read(self, size: int = 65535) -> bytes:
        return os.read(self._fd, size)

    def write(self, data: bytes) -> int:
        return os.write(self._fd, data)

    def close(self) -> None:
        if self._fd >= 0:
            try:
                os.close(self._fd)
            finally:
                self._fd = -1

    def __enter__(self) -> "TunTapDevice":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
