"""
reproducibility_check.py

동일 config를 N회 반복 실행하고 total_duration_sec의 분산을 측정한다.
변동계수(CV)와 Bootstrap 95% CI를 계산하여 실험 조건의 안정성을 평가한다.

판단 기준:
    CV < 10%  → 안정. 5회 반복으로 충분.
    10~20%    → 주의. 10회 이상 반복 필요.
    > 20%     → 위험. 실험 조건 재검토 필요 (Mock 레이턴시 고정 등).

사용법:
    python analyzer/reproducibility_check.py \\
        --config configs/queue_based_A.yaml \\
        --n 10 \\
        --logger-mode normal

    # 로깅 오버헤드 측정 (3단계 비교):
    python analyzer/reproducibility_check.py --config ... --logger-mode normal
    python analyzer/reproducibility_check.py --config ... --logger-mode disabled
    python analyzer/reproducibility_check.py --config ... --logger-mode null
"""

import argparse
import subprocess
import sys
import re
import time
import json
import numpy as np
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent


def run_single(config_path: str, logger_mode: str) -> float:
    """단일 실험을 실행하고 total_duration_sec을 반환한다."""
    runner = BASE_DIR / "runner" / "run_experiment.py"

    t_start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, str(runner), "--config", config_path, "--logger-mode", logger_mode],
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR)
    )
    t_end = time.perf_counter()

    wall_time = t_end - t_start

    # run_id를 파싱해서 metadata.json에서 duration을 읽으면 더 정확하지만,
    # stdout parse나 wall-clock 둘 다 허용한다.
    # wall-clock이 로깅 오버헤드 측정에는 더 정직하다.
    if result.returncode != 0:
        print(f"  [ERROR] Run failed:\n{result.stderr[-500:]}")
        return None

    return wall_time


def bootstrap_ci(data: list, n_resamples: int = 1000, ci: float = 95) -> tuple:
    data = np.array(data)
    boot_means = [
        np.mean(np.random.choice(data, size=len(data), replace=True))
        for _ in range(n_resamples)
    ]
    lower = np.percentile(boot_means, (100 - ci) / 2)
    upper = np.percentile(boot_means, 100 - (100 - ci) / 2)
    return lower, upper


def compute_stats(durations: list) -> dict:
    d = np.array(durations)
    mean = float(np.mean(d))
    std = float(np.std(d, ddof=1)) if len(d) > 1 else 0.0
    cv = std / mean if mean > 0 else 0.0
    ci_lower, ci_upper = bootstrap_ci(durations)

    return {
        "n": len(d),
        "mean_sec": round(mean, 4),
        "std_sec": round(std, 4),
        "cv": round(cv, 4),
        "cv_pct": round(cv * 100, 2),
        "min_sec": round(float(np.min(d)), 4),
        "max_sec": round(float(np.max(d)), 4),
        "ci_95_lower": round(ci_lower, 4),
        "ci_95_upper": round(ci_upper, 4),
        "is_stable_cv10": cv < 0.10,
        "is_acceptable_cv20": cv < 0.20,
        "recommendation": (
            "STABLE: 5 runs sufficient" if cv < 0.10
            else "CAUTION: 10+ runs recommended" if cv < 0.20
            else "DANGER: Review experiment conditions (fix mock latency, thread count, etc.)"
        )
    }


def main():
    parser = argparse.ArgumentParser(description="Reproducibility & Logging Overhead Checker")
    parser.add_argument("--config", required=True, help="Path to experiment config YAML")
    parser.add_argument("--n", type=int, default=10, help="Number of repeated runs (default: 10)")
    parser.add_argument(
        "--logger-mode",
        choices=["normal", "disabled", "null"],
        default="normal",
        help="Logger mode (use all three for overhead measurement)"
    )
    parser.add_argument(
        "--compare-all",
        action="store_true",
        help="Run all 3 logger modes sequentially and compare overhead"
    )
    parser.add_argument("--output", type=str, default=None, help="Optional JSON output path")
    args = parser.parse_args()

    modes = ["normal", "disabled", "null"] if args.compare_all else [args.logger_mode]
    results = {}

    for mode in modes:
        print(f"\n{'='*60}")
        print(f"Mode: {mode}  |  Config: {args.config}  |  Runs: {args.n}")
        print('='*60)

        durations = []
        for i in range(args.n):
            print(f"  Run {i+1}/{args.n} ... ", end="", flush=True)
            d = run_single(args.config, mode)
            if d is not None:
                durations.append(d)
                print(f"{d:.3f}s")
            else:
                print("FAILED")

        if not durations:
            print(f"  [ERROR] All runs failed for mode={mode}")
            continue

        stats = compute_stats(durations)
        results[mode] = stats

        print(f"\n--- Stats [{mode}] ---")
        print(f"  mean  : {stats['mean_sec']:.4f}s")
        print(f"  std   : {stats['std_sec']:.4f}s")
        print(f"  CV    : {stats['cv_pct']:.1f}%")
        print(f"  95% CI: [{stats['ci_95_lower']:.4f}, {stats['ci_95_upper']:.4f}]")
        print(f"  Judgment: {stats['recommendation']}")

    # Overhead analysis (compare-all mode)
    if args.compare_all and "normal" in results and "null" in results:
        print(f"\n{'='*60}")
        print("LOGGING OVERHEAD ANALYSIS")
        print('='*60)

        normal_mean = results["normal"]["mean_sec"]
        disabled_mean = results.get("disabled", {}).get("mean_sec", None)
        null_mean = results["null"]["mean_sec"]

        total_overhead = normal_mean - null_mean
        io_overhead = (normal_mean - disabled_mean) if disabled_mean else None
        call_overhead = (disabled_mean - null_mean) if disabled_mean else None

        print(f"  정상 로깅 평균       : {normal_mean:.4f}s")
        if disabled_mean:
            print(f"  Disabled 로거 평균   : {disabled_mean:.4f}s")
        print(f"  NullLogger 평균      : {null_mean:.4f}s")
        print(f"  ------------------------------------")
        print(f"  Total logging overhead  : {total_overhead:.4f}s ({total_overhead/normal_mean*100:.1f}%)")
        if io_overhead is not None:
            print(f"    +- I/O overhead       : {io_overhead:.4f}s ({io_overhead/normal_mean*100:.1f}%)")
            print(f"    +- Call overhead      : {call_overhead:.4f}s ({call_overhead/normal_mean*100:.1f}%)")

        results["_overhead_analysis"] = {
            "total_overhead_sec": round(total_overhead, 4),
            "io_overhead_sec": round(io_overhead, 4) if io_overhead else None,
            "call_overhead_sec": round(call_overhead, 4) if call_overhead else None,
            "total_overhead_pct_of_runtime": round(total_overhead / normal_mean * 100, 2),
        }

        print()
        print("  NOTE: Threshold = (max arch overhead - min arch overhead) / arch latency diff > 20% -> consider async logger")
        print("  (This number alone is not enough. Compare with inter-architecture latency difference.)")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({
                "config": args.config,
                "timestamp": datetime.now().isoformat(),
                "results": results
            }, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
