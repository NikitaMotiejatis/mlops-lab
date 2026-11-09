import argparse
import json
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

EXAMPLE = {"age": 45, "workclass": "Private", "education.num": 13, "marital.status": "Married-civ-spouse",
           "occupation": "Exec-managerial", "relationship": "Husband", "race": "White", "sex": "Male",
           "capital.gain": 0, "capital.loss": 0, "hours.per.week": 50, "native.country": "United-States"}


def one_request(url: str, body: bytes) -> tuple[float, bool]:
    req = urllib.request.Request(f"{url}/predict", data=body,
                                 headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            ok = resp.status == 200 and "prediction" in json.loads(resp.read())
    except Exception:
        ok = False
    return (time.perf_counter() - start) * 1000, ok


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8080")
    parser.add_argument("-n", "--requests", type=int, default=1000)
    parser.add_argument("-c", "--concurrency", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--payload", help="JSON file with one request body (default: built-in example)")
    parser.add_argument("--out", help="write the summary as JSON here")
    args = parser.parse_args()

    body = Path(args.payload).read_bytes() if args.payload else json.dumps(EXAMPLE).encode()
    health = json.loads(urllib.request.urlopen(f"{args.url}/health", timeout=10).read())
    for _ in range(args.warmup):                       # first calls are slower (lazy init)
        one_request(args.url, body)

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(lambda _: one_request(args.url, body), range(args.requests)))
    wall = time.perf_counter() - start

    lat = sorted(ms for ms, ok in results if ok)
    errors = sum(1 for _, ok in results if not ok)
    q = statistics.quantiles(lat, n=100, method="inclusive")   # q[49]=p50, q[94]=p95, q[98]=p99
    summary = {
        "url": args.url, "requests": args.requests, "concurrency": args.concurrency,
        "errors": errors, "model_version": health["model"].get("version"),
        "image_commit": health.get("image_commit"),
        "p50_ms": round(q[49], 1), "p95_ms": round(q[94], 1), "p99_ms": round(q[98], 1),
        "max_ms": round(lat[-1], 1), "mean_ms": round(statistics.mean(lat), 1),
        "throughput_rps": round(args.requests / wall, 1), "wall_s": round(wall, 2),
        "measured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    print(json.dumps(summary, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
