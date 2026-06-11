# Distributed Agent Simulation Summary Report

## 1. Overview
Generated from batch: `batch_sim_v4_20260606_050005`

## 2. Aggregate Metrics Data
| run_name                             |   throughput_req_per_sec_mean |   throughput_req_per_sec_std |   p50_latency_sec_mean |   p50_latency_sec_std |   p99_latency_sec_mean |   p99_latency_sec_std |   avg_queue_wait_sec_mean |   avg_queue_wait_sec_std |
|:-------------------------------------|------------------------------:|-----------------------------:|-----------------------:|----------------------:|-----------------------:|----------------------:|--------------------------:|-------------------------:|
| run_00_monolithic_TA_W1              |                         0.008 |                        0     |                125.992 |                 8.187 |                158.054 |                11.155 |                     0     |                    0     |
| run_01_master_worker_TA_W2           |                         0.015 |                        0     |                 66.103 |                 0.265 |                 68.17  |                 0.641 |                    31.565 |                    0.128 |
| run_02_master_worker_TA_W4           |                         0.03  |                        0     |                 33.695 |                 0.428 |                 34.503 |                 0.416 |                    15.22  |                    0.161 |
| run_03_master_worker_TA_W16          |                         0.102 |                        0.001 |                  9.756 |                 0.095 |                 10.588 |                 0.523 |                     3.043 |                    0.015 |
| run_04_master_worker_TA_W32          |                         0.167 |                        0.019 |                  5.453 |                 0.081 |                 12.566 |                 5.781 |                     1.008 |                    0.005 |
| run_05_queue_based_TA_W2             |                         0.015 |                        0     |                 65.686 |                 3.017 |                 76.219 |                 1.647 |                    31.467 |                    0.386 |
| run_06_queue_based_TA_W4             |                         0.03  |                        0     |                 33.452 |                 0.922 |                 36.673 |                 0.765 |                    14.954 |                    0.181 |
| run_07_queue_based_TA_W8             |                         0.057 |                        0     |                 17.556 |                 0.11  |                 18.785 |                 0.942 |                     6.928 |                    0.08  |
| run_08_queue_based_TA_W16            |                         0.095 |                        0.006 |                  9.954 |                 0.178 |                 20.79  |                11.999 |                     3.034 |                    0.032 |
| run_09_queue_based_TA_W32            |                         0.114 |                        0.025 |                  5.903 |                 0.2   |                 42.369 |                19.125 |                     1.076 |                    0.05  |
| run_10_swarm_TA_W4                   |                         0.029 |                        0     |                 34.061 |                 0.027 |                 36.521 |                 2.814 |                    15.25  |                    0.021 |
| run_11_swarm_TA_W8                   |                         0.056 |                        0.001 |                 17.724 |                 0.116 |                 20.981 |                 3.746 |                     7.069 |                    0.012 |
| run_12_swarm_TA_W16                  |                         0.103 |                        0.001 |                  9.657 |                 0.124 |                 10.283 |                 0.37  |                     3.046 |                    0.022 |
| run_13_swarm_TA_W32                  |                         0.189 |                        0.003 |                  5.341 |                 0.069 |                  6.442 |                 0.177 |                     1.015 |                    0.005 |
| run_14_monolithic_TB_W1              |                         0.143 |                        0.028 |                  6.006 |                 4.994 |                 17.003 |                 3.331 |                     0     |                    0     |
| run_15_master_worker_TB_W2           |                         0.159 |                        0.018 |                  3.351 |                 1.398 |                 15.85  |                 2.126 |                     0     |                    0     |
| run_16_queue_based_TB_W2             |                         0.046 |                        0.008 |                 19.332 |                 9.322 |                 30.102 |                 0.015 |                     0     |                    0     |
| run_17_swarm_TB_W2                   |                         0.416 |                        0.031 |                  2.34  |                 0.115 |                  4.153 |                 2.6   |                     0     |                    0     |
| run_18_queue_based_TA_W4_straggler   |                         0.023 |                        0.002 |                 84.047 |                 1.355 |                 94.596 |                12.285 |                    21.804 |                    0.687 |
| run_19_queue_based_TA_W4_straggler   |                         0.024 |                        0     |                 81.741 |                 1.439 |                 90.673 |                 2.51  |                    21.605 |                    0.725 |
| run_20_master_worker_TB_W2_straggler |                         0.188 |                        0.002 |                  5.31  |                 0.086 |                  5.849 |                 0.331 |                     0     |                    0     |
| run_21_queue_based_TB_W2_straggler   |                         0.033 |                        0     |                 30.081 |                 0.003 |                 30.105 |                 0.011 |                     0     |                    0     |
| run_22_master_worker_TA_W4_crash     |                        10.696 |                        0.2   |                  0.001 |                 0     |                  0.001 |                 0     |                     0     |                    0     |
| run_23_queue_based_TA_W4_crash       |                        10.628 |                        0.183 |                  0     |                 0     |                  0.001 |                 0     |                     0     |                    0     |
| run_24_master_worker_TA_W4_crash     |                         0.04  |                        0     |                 24.768 |                 0.328 |                 25.531 |                 0.236 |                    10.876 |                    0.041 |
| run_25_queue_based_TA_W4_crash       |                         0.024 |                        0     |                 82.979 |                 0.233 |                 86.799 |                 1.608 |                    21.518 |                    0.08  |

## 3. Charts
### Throughput
![Throughput](throughput.png)

### Latency
![Latency](latency.png)

### Communication Overhead (Task B)
![Overhead](overhead_task_b.png)
