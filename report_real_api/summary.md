# Distributed Agent Simulation Summary Report

## 1. Overview
Generated from batch: `real_batch_20260612_221830_fixed`

## 2. Aggregate Metrics Data
| run_name                              |   throughput_req_per_sec_mean |   throughput_req_per_sec_std |   p50_latency_sec_mean |   p50_latency_sec_std |   p99_latency_sec_mean |   p99_latency_sec_std |   avg_queue_wait_sec_mean |   avg_queue_wait_sec_std |   avg_master_aggregation_duration_ms_mean |   avg_master_aggregation_duration_ms_std |   avg_queue_lock_wait_ms_mean |   avg_queue_lock_wait_ms_std |
|:--------------------------------------|------------------------------:|-----------------------------:|-----------------------:|----------------------:|-----------------------:|----------------------:|--------------------------:|-------------------------:|------------------------------------------:|-----------------------------------------:|------------------------------:|-----------------------------:|
| 20260612_221830_monolithic_A_42e5923a |                         1.752 |                          nan |                  1.543 |                   nan |                  6.117 |                   nan |                         0 |                      nan |                                         0 |                                      nan |                             0 |                          nan |

*Note: Each run was executed with N=50 total requests to ensure statistical significance.* 

## 3. Charts
### Throughput
![Throughput](throughput.png)

### Latency
![Latency](latency.png)

