"""
Concurrent load / session-capacity stress test against a running Elimu Centric app.

Measures how many concurrent clients the current process can serve before
error rate or latency collapses. Also times key public routes for TTFB insight.

Usage:
  python stress_test_sessions.py
  python stress_test_sessions.py --base http://127.0.0.1:5000 --max-users 150
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple

import requests

# Avoid urllib3 connection-pool warnings drowning the report
import urllib3

urllib3.disable_warnings()


@dataclass
class RequestResult:
    ok: bool
    status: int
    elapsed_ms: float
    bytes: int
    error: str = ""
    has_session_cookie: bool = False


def percentile(sorted_vals: List[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def hit(
    session: requests.Session,
    url: str,
    timeout: float,
    method: str = "GET",
    data=None,
) -> RequestResult:
    t0 = time.perf_counter()
    try:
        if method == "POST":
            r = session.post(url, data=data, timeout=timeout, allow_redirects=False)
        else:
            r = session.get(url, timeout=timeout, allow_redirects=True)
        elapsed = (time.perf_counter() - t0) * 1000
        cookie_names = set(session.cookies.keys())
        has_sess = any(n.lower() in ("session", "sessionid") or "session" in n.lower() for n in cookie_names)
        # Flask default cookie is usually just "session"
        has_sess = has_sess or ("session" in cookie_names)
        ok = 200 <= r.status_code < 400
        return RequestResult(
            ok=ok,
            status=r.status_code,
            elapsed_ms=elapsed,
            bytes=len(r.content or b""),
            has_session_cookie=has_sess,
        )
    except Exception as e:
        elapsed = (time.perf_counter() - t0) * 1000
        return RequestResult(
            ok=False,
            status=0,
            elapsed_ms=elapsed,
            bytes=0,
            error=type(e).__name__ + ": " + str(e)[:120],
        )


def time_endpoints(base: str, timeout: float) -> dict:
    """Single-threaded baseline latency for key routes."""
    s = requests.Session()
    paths = [
        "/",
        "/login",
        "/static/css/custom.css",
        "/static/css/home-landing.css",
        "/static/css/school-site.css",
    ]
    out = {}
    for path in paths:
        # Warm once
        hit(s, base + path, timeout)
        samples = [hit(s, base + path, timeout).elapsed_ms for _ in range(5)]
        samples.sort()
        last = hit(s, base + path, timeout)
        out[path] = {
            "p50_ms": round(percentile(samples, 50), 1),
            "p95_ms": round(percentile(samples, 95), 1),
            "avg_ms": round(statistics.mean(samples), 1),
            "bytes": last.bytes,
            "status": last.status,
            "ok": last.ok,
            "error": last.error,
        }
    return out


def worker_session_loop(
    base: str,
    timeout: float,
    duration_sec: float,
    paths: List[str],
) -> Tuple[List[RequestResult], bool]:
    """
    One simulated live user: obtain a Flask session cookie, then keep requesting
    for duration_sec (mimics an open browser tab polling / navigating).
    """
    s = requests.Session()
    s.headers.update({"User-Agent": "EducenticStressTest/1.0", "Accept": "text/html"})
    results: List[RequestResult] = []

    # Establish session cookie via /login GET (sets CSRF / session)
    first = hit(s, base + "/login", timeout)
    results.append(first)
    has_cookie = first.has_session_cookie

    end = time.perf_counter() + duration_sec
    i = 0
    while time.perf_counter() < end:
        path = paths[i % len(paths)]
        results.append(hit(s, base + path, timeout))
        i += 1
        # Small think-time so we measure concurrency of live tabs, not pure hammer
        time.sleep(0.05)

    return results, has_cookie


def ramp_live_sessions(
    base: str,
    levels: List[int],
    hold_sec: float,
    timeout: float,
    paths: List[str],
) -> List[dict]:
    report = []
    for n in levels:
        print(f"\n=== Live sessions: {n} concurrent users for {hold_sec:.0f}s ===", flush=True)
        t0 = time.perf_counter()
        all_results: List[RequestResult] = []
        sessions_with_cookie = 0
        lock = threading.Lock()

        def run_one(_):
            nonlocal sessions_with_cookie
            res, has_c = worker_session_loop(base, timeout, hold_sec, paths)
            with lock:
                all_results.extend(res)
                if has_c:
                    sessions_with_cookie += 1
            return len(res)

        with ThreadPoolExecutor(max_workers=n) as pool:
            futs = [pool.submit(run_one, i) for i in range(n)]
            for f in as_completed(futs):
                try:
                    f.result()
                except Exception as e:
                    print(f"  worker failed: {e}", flush=True)

        wall = time.perf_counter() - t0
        elapsed = [r.elapsed_ms for r in all_results]
        elapsed_sorted = sorted(elapsed)
        oks = sum(1 for r in all_results if r.ok)
        fails = len(all_results) - oks
        err_rate = (fails / len(all_results) * 100) if all_results else 100.0
        # Status breakdown
        by_status = {}
        errors = {}
        for r in all_results:
            by_status[r.status] = by_status.get(r.status, 0) + 1
            if r.error:
                key = r.error.split(":")[0]
                errors[key] = errors.get(key, 0) + 1

        row = {
            "concurrent_users": n,
            "hold_sec": hold_sec,
            "wall_sec": round(wall, 2),
            "requests": len(all_results),
            "ok": oks,
            "fail": fails,
            "error_rate_pct": round(err_rate, 2),
            "rps": round(len(all_results) / wall, 2) if wall else 0,
            "p50_ms": round(percentile(elapsed_sorted, 50), 1),
            "p95_ms": round(percentile(elapsed_sorted, 95), 1),
            "p99_ms": round(percentile(elapsed_sorted, 99), 1),
            "max_ms": round(max(elapsed_sorted), 1) if elapsed_sorted else 0,
            "sessions_with_cookie": sessions_with_cookie,
            "status_counts": by_status,
            "error_types": errors,
            "healthy": err_rate < 5 and percentile(elapsed_sorted, 95) < 3000,
        }
        report.append(row)
        print(
            f"  req={row['requests']} ok={oks} fail={fails} err={err_rate:.1f}% "
            f"p50={row['p50_ms']}ms p95={row['p95_ms']}ms rps={row['rps']} "
            f"cookies={sessions_with_cookie}/{n} healthy={row['healthy']}",
            flush=True,
        )
        # Stop ramping hard once clearly broken (still record this level)
        if err_rate >= 25 or row["p95_ms"] >= 8000:
            print("  Stopping ramp — service degraded.", flush=True)
            break
    return report


def burst_hammer(base: str, concurrency: int, total_requests: int, timeout: float, path: str) -> dict:
    """Synchronous burst (no think-time) — finds hard ceiling of the HTTP server."""
    print(f"\n=== Burst: {total_requests} reqs @ {concurrency} workers -> {path} ===", flush=True)
    results: List[RequestResult] = []
    lock = threading.Lock()
    counter = {"i": 0}

    def one(_):
        s = requests.Session()
        r = hit(s, base + path, timeout)
        with lock:
            results.append(r)
            counter["i"] += 1
            if counter["i"] % 50 == 0:
                print(f"  … {counter['i']}/{total_requests}", flush=True)
        return r.ok

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        list(pool.map(one, range(total_requests)))
    wall = time.perf_counter() - t0
    elapsed_sorted = sorted(r.elapsed_ms for r in results)
    oks = sum(1 for r in results if r.ok)
    fails = len(results) - oks
    return {
        "path": path,
        "concurrency": concurrency,
        "total": len(results),
        "ok": oks,
        "fail": fails,
        "error_rate_pct": round(fails / len(results) * 100, 2) if results else 100,
        "wall_sec": round(wall, 2),
        "rps": round(len(results) / wall, 2) if wall else 0,
        "p50_ms": round(percentile(elapsed_sorted, 50), 1),
        "p95_ms": round(percentile(elapsed_sorted, 95), 1),
        "p99_ms": round(percentile(elapsed_sorted, 99), 1),
        "max_ms": round(max(elapsed_sorted), 1) if elapsed_sorted else 0,
    }


def estimate_capacity(ramp: List[dict]) -> dict:
    """Largest concurrent_users that stayed healthy; next level is the break point."""
    healthy = [r for r in ramp if r.get("healthy")]
    best = healthy[-1] if healthy else None
    first_bad = next((r for r in ramp if not r.get("healthy")), None)
    return {
        "comfortable_concurrent_live_sessions": best["concurrent_users"] if best else 0,
        "best_p95_ms": best["p95_ms"] if best else None,
        "best_error_rate_pct": best["error_rate_pct"] if best else None,
        "breaks_around": first_bad["concurrent_users"] if first_bad else None,
        "break_p95_ms": first_bad["p95_ms"] if first_bad else None,
        "break_error_rate_pct": first_bad["error_rate_pct"] if first_bad else None,
        "note": (
            "Flask cookie sessions are client-side (near-unlimited stored sessions). "
            "This measures concurrent active browsers the process can serve with "
            "acceptable latency under default debug server + DB_POOL_SIZE=8."
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5000")
    ap.add_argument("--hold", type=float, default=8.0, help="Seconds each live session stays active")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument(
        "--levels",
        default="5,10,20,40,60,80,100",
        help="Comma-separated concurrent user levels",
    )
    ap.add_argument("--out", default="stress_test_results.json")
    args = ap.parse_args()

    levels = [int(x.strip()) for x in args.levels.split(",") if x.strip()]
    paths = ["/", "/login", "/"]

    print(f"Target: {args.base}", flush=True)
    print("1) Baseline endpoint timings…", flush=True)
    baselines = time_endpoints(args.base, args.timeout)
    for path, m in baselines.items():
        print(
            f"  {path:40} p50={m['p50_ms']:7.1f}ms  p95={m['p95_ms']:7.1f}ms  "
            f"{m['bytes']:7d}B  status={m['status']}",
            flush=True,
        )

    print("\n2) Ramp live sessions (cookie + think-time)…", flush=True)
    ramp = ramp_live_sessions(args.base, levels, args.hold, args.timeout, paths)

    print("\n3) Burst hammer on /login (no think-time)…", flush=True)
    burst = burst_hammer(args.base, concurrency=40, total_requests=200, timeout=args.timeout, path="/login")
    print(
        f"  burst rps={burst['rps']} err={burst['error_rate_pct']}% "
        f"p50={burst['p50_ms']}ms p95={burst['p95_ms']}ms",
        flush=True,
    )

    capacity = estimate_capacity(ramp)
    payload = {
        "base": args.base,
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "server_note": "werkzeug debug (python app.py) — not production WSGI",
        "baselines": baselines,
        "ramp": ramp,
        "burst": burst,
        "capacity": capacity,
        "bottlenecks_observed": [
            "Default DB_POOL_SIZE=8 caps concurrent DB-backed HTML renders",
            "Werkzeug debug reloader is single-process / limited threads",
            "home() runs multiple DB queries per request (team, calendar, courses)",
            "HTML responses ~100KB+ increase TTFB under concurrency",
        ],
    }

    out_path = args.out
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"\nWrote {out_path}", flush=True)
    print(
        f"\nCAPACITY: ~{capacity['comfortable_concurrent_live_sessions']} comfortable "
        f"concurrent live sessions; breaks around {capacity['breaks_around']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
