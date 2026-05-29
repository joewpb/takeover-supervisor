#!/usr/bin/env python3
"""
Lightweight takeover supervisor — file-watcher + Telegram ping.

When Hermes hits a CAPTCHA or roadblock during browser automation:
1. Agent touches /tmp/takeover/stuck and describes the page to the user via chat
2. This supervisor sends a Telegram ping (so you notice even if you're away)
3. User responds in chat with instructions
4. Agent executes instructions, then touches /tmp/takeover/resume
5. Cycle resets — supervisor goes back to watching
"""

import os
import time
import signal
import sys

import requests

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT  = os.environ.get("TELEGRAM_CHAT", "")

SIG_DIR = "/tmp/takeover"
STUCK   = os.path.join(SIG_DIR, "stuck")
RESUME  = os.path.join(SIG_DIR, "resume")


def _safe_remove(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def _cleanup(*_args) -> None:
    print("\n[supervisor] shutting down...")
    _safe_remove(STUCK)
    _safe_remove(RESUME)
    print("[supervisor] done.")
    sys.exit(0)


def notify_telegram() -> None:
    """Send a simple Telegram ping — the agent handles the detailed page description."""
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT):
        print("[notify] creds missing — skipping Telegram")
        return
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={
                "chat_id": TELEGRAM_CHAT,
                "text": "🚨 Hermes hit a roadblock and needs your help. Check the chat for details.",
            },
            timeout=10,
        )
        if not resp.ok:
            print(f"[notify] Telegram API error: {resp.status_code} {resp.text[:200]}")
    except requests.RequestException as e:
        print(f"[notify] failed: {e}")


def supervise() -> None:
    os.makedirs(SIG_DIR, exist_ok=True)
    print("[supervisor] watching for stuck signal...")

    while True:
        if os.path.exists(STUCK):
            print("[supervisor] agent is stuck → notifying")
            notify_telegram()
            _safe_remove(STUCK)

            print("[supervisor] waiting for human to help...")
            while not os.path.exists(RESUME):
                time.sleep(1)
            _safe_remove(RESUME)
            print("[supervisor] resume received → agent continues")
        time.sleep(1)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, _cleanup)
    signal.signal(signal.SIGTERM, _cleanup)
    supervise()
