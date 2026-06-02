# Distributed Agent Simulation Summary Report

## 1. Overview
Generated from batch: `batch_20260602_224813`

## 2. Aggregate Metrics Data
| run_name                             |   throughput_req_per_sec_mean |   throughput_req_per_sec_std |   p50_latency_sec_mean |   p50_latency_sec_std |   p99_latency_sec_mean |   p99_latency_sec_std |   avg_queue_wait_sec_mean |   avg_queue_wait_sec_std |
|:-------------------------------------|------------------------------:|-----------------------------:|-----------------------:|----------------------:|-----------------------:|----------------------:|--------------------------:|-------------------------:|
| run_00_monolithic_TA_W1              |                         6.416 |                        0.138 |                  1.344 |                 0.073 |                  1.732 |                 0.04  |                     0     |                    0     |
| run_01_master_worker_TA_W2           |                         8.225 |                        0.107 |                  0.612 |                 0.008 |                  0.642 |                 0.018 |                     0.266 |                    0.003 |
| run_02_master_worker_TA_W4           |                         9.06  |                        0.031 |                  0.321 |                 0     |                  0.349 |                 0.01  |                     0.119 |                    0.001 |
| run_03_queue_based_TA_W2             |                         8.091 |                        0.207 |                  0.72  |                 0.007 |                  0.804 |                 0.022 |                     0.268 |                    0.004 |
| run_04_queue_based_TA_W4             |                         8.713 |                        0.079 |                  0.419 |                 0.007 |                  0.509 |                 0.016 |                     0.118 |                    0.002 |
| run_05_queue_based_TA_W8             |                         9.261 |                        0.053 |                  0.289 |                 0.001 |                  0.331 |                 0.012 |                     0.046 |                    0     |
| run_06_monolithic_TB_W1              |                         8.425 |                        0.253 |                  0.551 |                 0.035 |                  0.633 |                 0     |                     0     |                    0     |
| run_07_master_worker_TB_W2           |                         8.259 |                        0.097 |                  0.551 |                 0.009 |                  0.63  |                 0.034 |                     0.001 |                    0     |
| run_08_queue_based_TB_W2             |                         7.98  |                        0.129 |                  0.633 |                 0.017 |                  0.721 |                 0.006 |                     0     |                    0     |
| run_09_queue_based_TA_W4_straggler   |                         8.496 |                        0.056 |                  0.506 |                 0.027 |                  0.609 |                 0.001 |                     0.141 |                    0.001 |
| run_10_queue_based_TA_W4_straggler   |                         7.964 |                        0.059 |                  0.669 |                 0     |                  0.7   |                 0.012 |                     0.151 |                    0.002 |
| run_11_queue_based_TA_W4_straggler   |                         6.737 |                        0.032 |                  1.169 |                 0.001 |                  1.192 |                 0.006 |                     0.149 |                    0.002 |
| run_12_master_worker_TB_W2_straggler |                         4.224 |                        0.028 |                  2.047 |                 0.002 |                  2.117 |                 0.029 |                     0     |                    0     |
| run_13_queue_based_TB_W2_straggler   |                         4.143 |                        0.024 |                  2.087 |                 0.005 |                  2.146 |                 0.022 |                     0     |                    0     |
| run_14_swarm_TA_W4                   |                         9.467 |                        0.099 |                  0.078 |                 0     |                  0.092 |                 0.006 |                     0     |                    0     |
| run_15_swarm_TB_W2                   |                         8.294 |                        0.139 |                  0.543 |                 0.008 |                  0.611 |                 0.009 |                     0     |                    0     |
| run_16_swarm_TA_W8                   |                         9.516 |                        0.101 |                  0.078 |                 0     |                  0.138 |                 0.047 |                     0     |                    0     |
| run_17_master_worker_TA_W4_crash     |                         9.025 |                        0.055 |                  0.245 |                 0     |                  0.293 |                 0.021 |                     0.078 |                    0     |
| run_18_queue_based_TA_W4_crash       |                         0.286 |                        0.005 |                 34.303 |                 0.014 |                 36.625 |                 3.898 |                     0.002 |                    0     |

## 3. Charts
### Throughput
![Throughput](throughput.png)

### Latency
![Latency](latency.png)

### Communication Overhead (Task B)
![Overhead](overhead_task_b.png)
