"""
Stress-test authenticated page loads + their data-fetch APIs.

Uses a signed Flask session cookie (local SECRET_KEY) so we exercise real
dashboard HTML + JSON list endpoints without password guessing.

  python stress_test_data_pages.py
  python stress_test_data_pages.py --levels 5,10,20,40 --hold 8
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

import requests
import urllib3
from flask.sessions import SecureCookieSessionInterface

urllib3.disable_warnings()

try:
    from env_loader import load_project_env

    load_project_env(os.path.dirname(os.path.abspath(__file__)))
except Exception:
    pass


class _App:
    secret_key = os.environ.get("SECRET_KEY", "dev-only-change-this-locally")


def make_session_cookie(payload: dict) -> str:
    si = SecureCookieSessionInterface()
    serializer = si.get_signing_serializer(_App())
    if serializer is None:
        raise RuntimeError("Could not create session serializer")
    return serializer.dumps(dict(payload))


def percentile(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


TECH_SESSION = {
    "user_id": 1,
    "employee_id": "000000",
    "role": "technician",
    "full_name": "Stress Test Technician",
    "email": "stress@local.test",
    "_permanent": True,
}

# HTML shell pages + the JSON data fetches their loaders call after paint
TARGETS: List[Dict[str, Any]] = [
    {
        "name": "employee_dashboard",
        "kind": "page",
        "path": "/dashboard/employee",
        "accept": "text/html",
    },
    {
        "name": "setup_guide_status",
        "kind": "api",
        "path": "/dashboard/employee/setup-guide-status",
        "accept": "application/json",
    },
    {
        "name": "student_fees_page",
        "kind": "page",
        "path": "/dashboard/employee/student-fees",
        "accept": "text/html",
    },
    {
        "name": "student_fees_students_api",
        "kind": "api",
        "path": "/dashboard/employee/student-fees/students?page=1&per_page=50",
        "accept": "application/json",
    },
    {
        "name": "finance_overview_page",
        "kind": "page",
        "path": "/dashboard/employee/finance-overview",
        "accept": "text/html",
    },
    {
        "name": "finance_overview_students_api",
        "kind": "api",
        "path": "/dashboard/employee/finance-overview/students?page=1&per_page=50",
        "accept": "application/json",
    },
    {
        "name": "fees_reports_page",
        "kind": "page",
        "path": "/dashboard/employee/fees-reports",
        "accept": "text/html",
    },
    {
        "name": "staff_salaries_page",
        "kind": "page",
        "path": "/dashboard/employee/staff-and-salaries",
        "accept": "text/html",
    },
    {
        "name": "staff_employees_api",
        "kind": "api",
        "path": "/staff-management/employees?page=1&per_page=50",
        "accept": "application/json",
    },
    {
        "name": "staff_stats_api",
        "kind": "api",
        "path": "/staff-management/stats",
        "accept": "application/json",
    },
    {
        "name": "find_student_page",
        "kind": "page",
        "path": "/dashboard/employee/find-student",
        "accept": "text/html",
    },
    {
        "name": "exams_grades_page",
        "kind": "page",
        "path": "/dashboard/employee/exams-and-grades",
        "accept": "text/html",
    },
    {
        "name": "my_classes_page",
        "kind": "page",
        "path": "/dashboard/employee/my-classes",
        "accept": "text/html",
    },
]

# Realistic browser flows: open shell then fetch list data
FLOWS: List[Dict[str, Any]] = [
    {
        "name": "student_fees_flow",
        "steps": [
            "/dashboard/employee/student-fees",
            "/dashboard/employee/student-fees/students?page=1&per_page=50",
        ],
    },
    {
        "name": "finance_overview_flow",
        "steps": [
            "/dashboard/employee/finance-overview",
            "/dashboard/employee/finance-overview/students?page=1&per_page=50",
        ],
    },
    {
        "name": "staff_management_flow",
        "steps": [
            "/dashboard/employee/staff-and-salaries",
            "/staff-management/employees?page=1&per_page=50",
            "/staff-management/stats",
        ],
    },
    {
        "name": "dashboard_home_flow",
        "steps": [
            "/dashboard/employee",
            "/dashboard/employee/setup-guide-status",
        ],
    },
]


def authed_session(cookie_value: str) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": "EducenticDataStress/1.0",
            "Accept": "text/html,application/json",
        }
    )
    s.cookies.set("session", cookie_value, domain="127.0.0.1", path="/")
    return s


def hit(session: requests.Session, base: str, path: str, accept: str, timeout: float) -> Dict[str, Any]:
    t0 = time.perf_counter()
    try:
        r = session.get(
            base + path,
            timeout=timeout,
            headers={"Accept": accept},
            allow_redirects=True,
        )
        ms = (time.perf_counter() - t0) * 1000
        redirected_login = "/login" in (r.url or "")
        ok = (200 <= r.status_code < 400) and not redirected_login
        ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip()
        body_ok = True
        rows = None
        if "json" in accept and ok:
            try:
                data = r.json()
                if isinstance(data, dict) and data.get("success") is False:
                    body_ok = False
                if isinstance(data, dict):
                    for key in ("students", "employees", "items", "rows"):
                        if key in data and isinstance(data[key], list):
                            rows = len(data[key])
                            break
            except Exception:
                body_ok = False
        return {
            "ok": ok and body_ok,
            "status": r.status_code,
            "ms": ms,
            "bytes": len(r.content or b""),
            "ctype": ctype,
            "rows": rows,
            "redirect_login": redirected_login,
            "error": "" if (ok and body_ok) else ("login_redirect" if redirected_login else f"status={r.status_code}"),
        }
    except Exception as e:
        ms = (time.perf_counter() - t0) * 1000
        return {
            "ok": False,
            "status": 0,
            "ms": ms,
            "bytes": 0,
            "ctype": "",
            "rows": None,
            "redirect_login": False,
            "error": f"{type(e).__name__}: {str(e)[:100]}",
        }


def baseline(base: str, cookie: str, timeout: float) -> List[dict]:
    s = authed_session(cookie)
    out = []
    print("\n=== Baseline (authenticated page + data fetches) ===", flush=True)
    for t in TARGETS:
        # warm
        hit(s, base, t["path"], t["accept"], timeout)
        samples = [hit(s, base, t["path"], t["accept"], timeout) for _ in range(4)]
        ms = [x["ms"] for x in samples]
        ok_n = sum(1 for x in samples if x["ok"])
        last = samples[-1]
        row = {
            "name": t["name"],
            "kind": t["kind"],
            "path": t["path"],
            "p50_ms": round(percentile(ms, 50), 1),
            "p95_ms": round(percentile(ms, 95), 1),
            "avg_ms": round(statistics.mean(ms), 1),
            "bytes": last["bytes"],
            "rows": last.get("rows"),
            "ok_rate": round(ok_n / len(samples) * 100, 1),
            "last_status": last["status"],
            "last_error": last.get("error") or "",
        }
        out.append(row)
        mark = "OK" if ok_n == len(samples) else "FAIL"
        extra = f" rows={last.get('rows')}" if last.get("rows") is not None else ""
        print(
            f"  [{mark}] {t['name']:32} p50={row['p50_ms']:7.1f}ms p95={row['p95_ms']:7.1f}ms "
            f"{row['bytes']:7d}B{extra}",
            flush=True,
        )
    return out


def flow_once(session: requests.Session, base: str, flow: dict, timeout: float) -> List[dict]:
    results = []
    for path in flow["steps"]:
        accept = "application/json" if ("students" in path or "employees" in path or "stats" in path or "status" in path) else "text/html"
        if path.endswith("/stats") or "setup-guide" in path:
            accept = "application/json"
        r = hit(session, base, path, accept, timeout)
        r["flow"] = flow["name"]
        r["path"] = path
        results.append(r)
    return results


def ramp_flows(base: str, cookie: str, levels: List[int], hold: float, timeout: float) -> List[dict]:
    report = []
    print("\n=== Ramp: concurrent users running page+data flows ===", flush=True)
    for n in levels:
        print(f"\n--- {n} concurrent authenticated users, {hold:.0f}s ---", flush=True)
        all_hits: List[dict] = []
        lock = threading.Lock()

        def worker(i: int):
            s = authed_session(cookie)
            end = time.perf_counter() + hold
            local = []
            fi = 0
            while time.perf_counter() < end:
                flow = FLOWS[fi % len(FLOWS)]
                local.extend(flow_once(s, base, flow, timeout))
                fi += 1
                time.sleep(0.08)
            with lock:
                all_hits.extend(local)

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=n) as pool:
            futs = [pool.submit(worker, i) for i in range(n)]
            for f in as_completed(futs):
                f.result()
        wall = time.perf_counter() - t0

        ms = [h["ms"] for h in all_hits]
        oks = sum(1 for h in all_hits if h["ok"])
        fails = len(all_hits) - oks
        err = (fails / len(all_hits) * 100) if all_hits else 100.0

        # per-path rollup
        by_path: Dict[str, List[float]] = {}
        fail_by_path: Dict[str, int] = {}
        for h in all_hits:
            p = h.get("path") or "?"
            by_path.setdefault(p, []).append(h["ms"])
            if not h["ok"]:
                fail_by_path[p] = fail_by_path.get(p, 0) + 1
        path_stats = []
        for p, vals in by_path.items():
            path_stats.append(
                {
                    "path": p,
                    "n": len(vals),
                    "p50_ms": round(percentile(vals, 50), 1),
                    "p95_ms": round(percentile(vals, 95), 1),
                    "fails": fail_by_path.get(p, 0),
                }
            )
        path_stats.sort(key=lambda x: x["p95_ms"], reverse=True)

        row = {
            "concurrent_users": n,
            "requests": len(all_hits),
            "ok": oks,
            "fail": fails,
            "error_rate_pct": round(err, 2),
            "rps": round(len(all_hits) / wall, 2) if wall else 0,
            "p50_ms": round(percentile(ms, 50), 1),
            "p95_ms": round(percentile(ms, 95), 1),
            "p99_ms": round(percentile(ms, 99), 1),
            "max_ms": round(max(ms), 1) if ms else 0,
            "wall_sec": round(wall, 2),
            "healthy": err < 5 and percentile(ms, 95) < 4000,
            "slowest_paths": path_stats[:6],
        }
        report.append(row)
        print(
            f"  req={row['requests']} ok={oks} fail={fails} err={err:.1f}% "
            f"p50={row['p50_ms']}ms p95={row['p95_ms']}ms rps={row['rps']} healthy={row['healthy']}",
            flush=True,
        )
        if path_stats:
            print("  slowest:", flush=True)
            for ps in path_stats[:4]:
                print(
                    f"    p95={ps['p95_ms']:7.1f}ms n={ps['n']:4d} fails={ps['fails']}  {ps['path']}",
                    flush=True,
                )
        if err >= 20 or row["p95_ms"] >= 10000:
            print("  Stopping ramp — degraded.", flush=True)
            break
    return report


def estimate(ramp: List[dict]) -> dict:
    healthy = [r for r in ramp if r.get("healthy")]
    best = healthy[-1] if healthy else None
    bad = next((r for r in ramp if not r.get("healthy")), None)
    return {
        "comfortable_concurrent_data_users": best["concurrent_users"] if best else 0,
        "best_p95_ms": best["p95_ms"] if best else None,
        "breaks_around": bad["concurrent_users"] if bad else None,
        "break_p95_ms": bad["p95_ms"] if bad else None,
        "break_error_rate_pct": bad["error_rate_pct"] if bad else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5000")
    ap.add_argument("--hold", type=float, default=8.0)
    ap.add_argument("--timeout", type=float, default=45.0)
    ap.add_argument("--levels", default="5,10,20,40,60")
    ap.add_argument("--out", default="stress_test_data_results.json")
    args = ap.parse_args()

    levels = [int(x.strip()) for x in args.levels.split(",") if x.strip()]
    cookie = make_session_cookie(TECH_SESSION)
    print(f"Target: {args.base}", flush=True)
    print(f"Auth: forged technician session (employee_id={TECH_SESSION['employee_id']})", flush=True)

    # Auth check
    s = authed_session(cookie)
    probe = hit(s, args.base, "/dashboard/employee", "text/html", args.timeout)
    if not probe["ok"]:
        print(f"AUTH FAILED: {probe}", flush=True)
        return 1
    print(f"Auth OK: dashboard {probe['ms']:.0f}ms / {probe['bytes']}B", flush=True)

    baselines = baseline(args.base, cookie, args.timeout)
    ramp = ramp_flows(args.base, cookie, levels, args.hold, args.timeout)
    capacity = estimate(ramp)

    # Rank slowest endpoints from baseline
    slow = sorted(baselines, key=lambda x: x["p95_ms"], reverse=True)

    payload = {
        "base": args.base,
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "auth": "forged_technician_session",
        "server_note": "werkzeug debug + DB_POOL_SIZE from env",
        "baselines": baselines,
        "slowest_baselines": slow[:8],
        "ramp": ramp,
        "capacity": capacity,
        "flows": [f["name"] for f in FLOWS],
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"\nWrote {args.out}", flush=True)
    print(
        f"CAPACITY: ~{capacity['comfortable_concurrent_data_users']} concurrent users "
        f"comfortably loading pages+data; breaks around {capacity['breaks_around']}",
        flush=True,
    )
    print("\nSlowest endpoints (baseline p95):", flush=True)
    for b in slow[:6]:
        print(f"  {b['p95_ms']:7.1f}ms  {b['name']}  ({b['kind']})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
