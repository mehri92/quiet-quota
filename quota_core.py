"""Read-only Codex usage transport and persistent threshold policy (stdlib only)."""
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
from i18n import LANGUAGES

DEFAULTS = {"thresholds": [50, 75, 90, 95], "corner": "bottom-right",
            "duration_ms": 4000, "poll_seconds": 120, "monitor": 0,
            "animations": True, "language": "en"}


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def validate_config(data):
    if not isinstance(data, dict):
        raise ValueError("bad_settings")
    cfg = DEFAULTS | data
    if not isinstance(cfg["language"], str) or cfg["language"] not in LANGUAGES:
        cfg["language"] = "en"
    values = cfg["thresholds"]
    if not isinstance(values, list) or not values or any(
        type(x) is not int or not 1 <= x <= 100 for x in values
    ):
        raise ValueError("bad_thresholds")
    cfg["thresholds"] = sorted(set(values))
    if cfg["corner"] not in ("top-left", "top-right", "bottom-left", "bottom-right"):
        raise ValueError("bad_settings")
    for key, low, high in (("duration_ms", 1000, 15000), ("poll_seconds", 60, 1800),
                           ("monitor", 0, 32)):
        if type(cfg[key]) is not int or not low <= cfg[key] <= high:
            raise ValueError("bad_settings")
    if type(cfg["animations"]) is not bool:
        raise ValueError("bad_settings")
    return cfg


def weekly_snapshot(result, now=None):
    """Only select the codex bucket and an explicitly seven-day window."""
    now = time.time() if now is None else now
    buckets = result.get("rateLimitsByLimitId") or {}
    bucket = buckets.get("codex") if buckets else result.get("rateLimits")
    if not isinstance(bucket, dict) or bucket.get("limitId") not in (None, "codex"):
        raise ValueError("no_bucket")
    windows = [bucket.get(k) for k in ("primary", "secondary")]
    windows = [w for w in windows if isinstance(w, dict) and w.get("windowDurationMins") == 10080]
    if len(windows) != 1:
        raise ValueError("no_week")
    window = windows[0]
    used, reset = window.get("usedPercent"), window.get("resetsAt")
    if (isinstance(used, bool) or not isinstance(used, (float, int)) or
            not math.isfinite(used) or not 0 <= used <= 100):
        raise ValueError("invalid_usage")
    if type(reset) not in (int, float) or not math.isfinite(reset) or reset <= now:
        raise ValueError("stale_data")
    return {"used": used, "reset": int(reset)}


class ThresholdPolicy:
    def __init__(self, path):
        self.path = Path(path)
        try:
            self.state = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(self.state, dict):
                self.state = {}
        except (OSError, ValueError):
            self.state = {}

    def observe(self, identity, snap, thresholds, paused=False, now=None):
        now = time.time() if now is None else now
        reached = {t for t in thresholds if snap["used"] >= t}
        old = self.state.get(identity)
        # First installation/account switch establishes a silent baseline.
        if not isinstance(old, dict) or "reset" not in old or "seen" not in old:
            self.state[identity] = {"reset": snap["reset"], "seen": sorted(reached)}
            atomic_json(self.path, self.state)
            return False
        # Tolerate small timestamp corrections; an elapsed old window plus a
        # later server reset, or a materially changed reset, starts a new cycle.
        changed = abs(old["reset"] - snap["reset"]) > 300
        elapsed = now >= old["reset"] and snap["reset"] > old["reset"]
        seen = set() if changed or elapsed else set(old["seen"])
        new = reached - seen
        if not paused:
            seen.update(reached)
        self.state[identity] = {"reset": snap["reset"], "seen": sorted(seen)}
        atomic_json(self.path, self.state)
        return bool(new) and not paused


def codex_command():
    exe = shutil.which("codex.exe") or shutil.which("codex")
    if not exe:
        raise RuntimeError("missing_cli")
    path = Path(exe)
    if path.suffix.lower() in (".cmd", ".bat", ".ps1"):
        # npm's Windows shim delegates to this JS entrypoint. Bypass cmd.exe
        # entirely so spaces/metacharacters in paths never become shell code.
        entry = path.parent / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
        node = shutil.which("node.exe") or shutil.which("node")
        if not entry.is_file() or not node:
            raise RuntimeError("missing_entry")
        return [node, str(entry), "app-server"]
    return [str(path), "app-server"]


class CodexReader:
    def __init__(self, command=None, cancel=None):
        self.command = command
        self.cancel = cancel or threading.Event()
        self.proc = None
        self.serial = 0
        self.messages = queue.Queue()

    def start(self):
        if self.proc and self.proc.poll() is None:
            return
        self.close()
        self.messages = queue.Queue()
        self.proc = subprocess.Popen(
            self.command or codex_command(), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            encoding="utf-8", errors="replace", bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            start_new_session=os.name != "nt")
        stream, messages = self.proc.stdout, self.messages

        def drain():
            try:
                for line in stream:
                    try:
                        item = json.loads(line)
                        if isinstance(item, dict):
                            messages.put(item)
                    except ValueError:
                        continue
            finally:
                stream.close()
                messages.put(None)
        threading.Thread(target=drain, daemon=True).start()
        self.rpc("initialize", {"clientInfo": {"name": "quiet_quota",
                 "title": "Quiet Quota", "version": "0.2.2"}})
        self.send({"method": "initialized", "params": {}})

    def send(self, message):
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def rpc(self, method, params=None, timeout=25):
        self.serial += 1
        request_id = self.serial
        message = {"id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        self.send(message)
        deadline = time.monotonic() + timeout
        while True:
            if self.cancel.is_set():
                raise RuntimeError("cancelled")
            try:
                item = self.messages.get(timeout=max(.01, min(.25, deadline-time.monotonic())))
            except queue.Empty:
                if time.monotonic() >= deadline:
                    raise RuntimeError("timeout") from None
                continue
            if item is None:
                raise RuntimeError("disconnected")
            if "method" in item and "id" in item:
                self.send({"id": item["id"], "error": {"code": -32601,
                           "message": "Read-only usage monitor; request not supported"}})
            elif item.get("id") == request_id:
                if "error" in item:
                    # Never put raw upstream replies or credentials into logs.
                    raise RuntimeError("rpc_error")
                return item.get("result", {})
            if time.monotonic() >= deadline:
                raise RuntimeError("timeout")

    def read(self):
        self.start()
        account = self.rpc("account/read", {"refreshToken": False}).get("account")
        if not isinstance(account, dict) or account.get("type") != "chatgpt":
            raise RuntimeError("sign_in")
        identity = hashlib.sha256(json.dumps(account, sort_keys=True).encode()).hexdigest()[:24]
        return identity, weekly_snapshot(self.rpc("account/rateLimits/read"))

    def close(self):
        proc, self.proc = self.proc, None
        if not proc:
            return
        if proc.poll() is None:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW, timeout=5)
            else:
                import signal
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        if proc.stdin:
            proc.stdin.close()


class Poller(threading.Thread):
    def __init__(self, events, interval=120):
        super().__init__(daemon=True)
        self.events, self.interval = events, interval
        self.stop_event, self.wake = threading.Event(), threading.Event()

    def run(self):
        reader, failures = CodexReader(cancel=self.stop_event), 0
        try:
            while not self.stop_event.is_set():
                try:
                    identity, snap = reader.read()
                    self.events.put(("usage", identity, snap))
                    failures = 0
                except Exception as exc:
                    failures += 1
                    # Only known, sanitised messages leave the worker.
                    message = str(exc) if isinstance(exc, (RuntimeError, ValueError)) else "connection_failed"
                    self.events.put(("error", message))
                    reader.close()
                self.wake.wait(min(900, self.interval * 2 ** min(failures, 3)))
                self.wake.clear()
        finally:
            reader.close()

    def stop(self):
        self.stop_event.set()
        self.wake.set()
