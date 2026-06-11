import argparse
import pandas as pd
import numpy as np
from scipy.stats import spearmanr, pearsonr
import statsmodels.api as sm
from pathlib import Path

def analyze_correlations(input_csv: str, output_md: str):
    df = pd.read_csv(input_csv)
    
    # We need to compute correlations.
    # The benchmark dataset has columns like p99_latency_sec_mean, avg_queue_depth_mean, etc.
    # But wait, correlation should be calculated on the raw runs (summary.csv), not the aggregated benchmark dataset.
    # Let's assume input_csv is the raw summary.csv from the batch run!
    
    metrics_to_correlate = {
        "Queue_Depth_vs_p99": ("avg_queue_depth", "p99_latency_sec"),
        "Utilization_vs_Throughput": ("utilization_busy", "throughput_req_per_sec"),
        "Retry_vs_Latency": ("retries", "p50_latency_sec"),
        "RateLimit_vs_Throughput": ("api_429_errors", "throughput_req_per_sec")
    }
    
    report_lines = [
        "# Bottleneck Correlation Analysis",
        "",
        "> [!IMPORTANT]",
        "> 본 보고서는 Phase 2B의 병목 현상 상관관계 분석 결과입니다. 지표 간의 상관관계(Correlation)를 나타내며, 반드시 인과관계(Causation)를 의미하지는 않습니다.",
        "",
        "## 1. Pairwise Correlation (Spearman & Pearson)",
        "",
        "| Relationship | Spearman (Primary) | Pearson (Secondary) | N |",
        "|---|---|---|---|"
    ]
    
    for rel_name, (col_x, col_y) in metrics_to_correlate.items():
        if col_x in df.columns and col_y in df.columns:
            # Filter out NaNs
            valid_df = df.dropna(subset=[col_x, col_y])
            n = len(valid_df)
            if n > 1:
                spearman_corr, p_s = spearmanr(valid_df[col_x], valid_df[col_y])
                pearson_corr, p_p = pearsonr(valid_df[col_x], valid_df[col_y])
                report_lines.append(f"| {rel_name} | {spearman_corr:.4f} (p={p_s:.4f}) | {pearson_corr:.4f} (p={p_p:.4f}) | {n} |")
            else:
                report_lines.append(f"| {rel_name} | N/A | N/A | {n} |")
        else:
            report_lines.append(f"| {rel_name} | Missing columns | Missing columns | 0 |")
            
    report_lines.append("")
    report_lines.append("## 2. Multiple Regression Analysis")
    report_lines.append("")
    report_lines.append("수식: `Latency = a * QueueDepth + b * RetryCount + c * Utilization`")
    report_lines.append("")
    
    # Dependent variable: p99_latency_sec
    # Independent variables: avg_queue_depth, retries, utilization_busy
    target_y = "p99_latency_sec"
    target_xs = ["avg_queue_depth", "retries", "utilization_busy"]
    
    missing_cols = [c for c in [target_y] + target_xs if c not in df.columns]
    if missing_cols:
        report_lines.append(f"> [!WARNING]\n> 누락된 컬럼으로 인해 다중 회귀 분석을 수행할 수 없습니다: {missing_cols}\n")
    else:
        # Standardize the variables so coefficients are comparable (beta weights)
        valid_df = df.dropna(subset=[target_y] + target_xs)
        if len(valid_df) > 3:
            X = valid_df[target_xs]
            y = valid_df[target_y]
            
            # Standardization
            X_std = (X - X.mean()) / X.std()
            y_std = (y - y.mean()) / y.std()
            
            # Add constant
            X_std = sm.add_constant(X_std)
            
            # OLS Model
            model = sm.OLS(y_std, X_std)
            results = model.fit()
            
            report_lines.append("### Standardized Coefficients (Beta Weights)")
            report_lines.append("")
            report_lines.append("| Predictor | Beta Coefficient | p-value |", )
            report_lines.append("|---|---|---|")
            
            for predictor in target_xs:
                coef = results.params.get(predictor, 0.0)
                p_val = results.pvalues.get(predictor, 1.0)
                report_lines.append(f"| {predictor} | {coef:.4f} | {p_val:.4f} |")
                
            report_lines.append("")
            report_lines.append(f"**R-squared**: {results.rsquared:.4f}")
            report_lines.append("")
            
            # Identify strongest predictor
            coefs_abs = {p: abs(results.params.get(p, 0)) for p in target_xs}
            strongest = max(coefs_abs, key=coefs_abs.get)
            report_lines.append(f"> [!TIP]\n> 표준화된 계수(Beta)의 절댓값이 가장 큰 예측 인자(Strongest Predictor)는 **{strongest}** 입니다. 이는 해당 변수가 Latency(p99) 변동을 가장 잘 설명함을 시사합니다.\n")
        else:
            report_lines.append("> [!WARNING]\n> 유효한 데이터 샘플 수가 부족하여 다중 회귀 분석을 수행할 수 없습니다.\n")
            
    with open(output_md, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print(f"Correlation report successfully generated at {output_md}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_csv", type=str, required=True, help="Path to the raw summary CSV (run-level data) from batch experiments")
    parser.add_argument("--output_md", type=str, required=True, help="Path to the output Markdown report")
    args = parser.parse_args()
    
    analyze_correlations(args.input_csv, args.output_md)
