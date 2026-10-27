"""
Keeps a Render free-tier instance from spinning down.

Render puts free web services to sleep after 15 minutes without
inbound traffic. This thread requests the service's own public URL
every few minutes, which goes through Render's load balancer and
counts as traffic.

Configuration (environment variables):
    KEEPALIVE_URL               URL to ping. Defaults to
                                $RENDER_EXTERNAL_URL/health, which Render
                                sets automatically.
    KEEPALIVE_INTERVAL_SECONDS  Default 600 (10 minutes).
    KEEPALIVE_ENABLED           Set to "0" to disable.

When neither KEEPALIVE_URL nor RENDER_EXTERNAL_URL is set (e.g. running
locally on Windows/macOS/Linux) the thread does nothing.
"""

import os
import threading
import time
import urllib.request


def _target_url():

    url = os.getenv("KEEPALIVE_URL")

    if url:
        return url

    base = os.getenv("RENDER_EXTERNAL_URL")

    if base:
        return base.rstrip("/") + "/health"

    return None


def _loop(url, interval):

    # Let the server finish starting first
    time.sleep(min(60, interval))

    while True:

        try:

            request = urllib.request.Request(
                url,
                headers={"User-Agent": "scaffold-analyzer-keepalive"}
            )

            with urllib.request.urlopen(request, timeout=30) as response:
                response.read(256)

        except Exception as error:

            print(f"Keep-alive ping failed: {error}")

        time.sleep(interval)


def start_keepalive():

    if os.getenv("KEEPALIVE_ENABLED", "1") == "0":
        return False

    url = _target_url()

    if not url:
        return False

    interval = int(os.getenv("KEEPALIVE_INTERVAL_SECONDS", "600"))

    thread = threading.Thread(
        target=_loop,
        args=(url, max(60, interval)),
        name="keepalive",
        daemon=True
    )

    thread.start()

    print(f"Keep-alive enabled: pinging {url} every {interval}s")

    return True
