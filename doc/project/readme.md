# PTP-Perf

A survey of PTP time-synchronization considerations. This work is conducted at the University of British Columbia.

### Project Plan

The survey project is structured into the following rough components: a preliminary stage for collecting initial measurements, and several extensions of the basics. 

_Note: This doesn't render correctly on GitHub yet because GitHub uses an old version of mermaid_
```mermaid
%% Prompt: 6 month time plan from january (Gantt)
gantt
    dateFormat  YYYY-MM-DD
    axisFormat %d.%m
    title PTP Research Time Plan
    
    section Preliminary
    Literature Review :a1, 2022-01-08, 2w
    Hardware and Software Setup :a2, 2022-01-08, 2w
    Preliminary Results with 2 Vendors :a3, 2022-01-15, 2w
    
    section More In-depth
    Add additional vendors :a4, 2022-01-29, 2w
    More accurate clock difference :a5, 2022-02-05, 2w
    Basics covered :basics, after a5, 2d
    
    section Extensions
    Scalability :scalability, after basics, 2w
    2nd Hardware Platform :2nd-hardware, after basics, 3w
    Resource Contention :contention, after scalability, 3w
    Extensions covered :extensions, after contention, 2d
    
    section Paper
    Write paper: write, after extensions, 3w
    Review and edits: review, after write, 1w

    section Additional
    Additional improvements: additional, after extensions, 4w

    section Finalization
    Finalization: finalization, after review, 4w
```

### Planned Experiments

We aim to collect data for the following experiments:

| Name                       | Description                                                                                                                                                                                                                                                                                                                                                                                    |
|----------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Baseline**               | 📊 1-1 Synchronization quality<br><br>Potential Metrics:<br>    Clock difference (synchronization quality)<br>    Convergence time<br>    Jitter (metric?) <br> Difference between reported clock offset and actual clock offset.                                                                                                                                                              |
| **Resilience**             | Measure relative performance when contention is present. These are categorized into a set for each hardware component.<br>- CPU contention <br>- Network contention<br><br> Contention can be generated e.g. using iPerf for network traffic and stress-ng. Stress could also be placed with with differing levels of intensity                                                                |
| - Unprioritized contention | 📊 Net: Contention same interface & traffic class<br> 📊 CPU: Contention on same core<br>⚙️ For each: Load level 0%, 10%, 20%, 30%, 40%, 50%, 60%, 70%, 80%, 90%, 100%                                                                                                                                                                                                                         |
| - Prioritized contention   | 📊 Net: Contention on lower traffic class.<br>📊 CPU: Contention on same core, lower priority.                                                                                                                                                                                                                                                                                                 |
| - Isolated contention      | 📊 Net: Contention on other interface.<br> 📊 CPU: Contention on other cores via task affinity.                                                                                                                                                                                                                                                                                                |
| **Scalability**            | Synchronization across switch using more nodes<br><br>More hardware intensive, need compatible switch and access to more nodes                                                                                                                                                                                                                                                                 |
| - 4 Boards                 | 📊 Conduct experiment with 4 Raspberry Pis. Determine whether key quality metrics differ.                                                                                                                                                                                                                                                                                                      |
| **Fault Tolerance**        | Examine node instability effects on the rest of the cluster.<br><br>Faults can occur on two different types of nodes:<br>⚙️ Slave clock (the simple setup)<br>Master clock (more difficult, should the selection of a new master clock be allowed?)<br>&rarr; ⚙️ New master clock: Determine time to reconvergence<br>&rarr; ⚙️ No new master clock: Determine divergence rate between clocks. |
| - Software Fault           | 📊 Daemon crash.                                                                                                                                                                                                                                                                                                                                                                               |
| - Hardware Fault           | 📊 Disruption in network connectivity.                                                                                                                                                                                                                                                                                                                                                         |
| _- Adverse PTP Client_     | ❓ Lower priority: Determine if possible and/or desirable.                                                                                                                                                                                                                                                                                                                                      |
| ***Network Topology***     | ❓ Verify if and how this should be achieved.                                                                                                                                                                                                                                                                                                                                                   |

### Literature
For a list of related works, see [here](literature.md).

### Vendors

PTP-Perf can currently collect metrics from 2 PTP time synchronization vendors: PTPd and LinuxPTP. PTPd is a general software implementation of the PTP protocol while LinuxPTP is tied specifically to the Linux kernel. The former is the easier of the two to deploy, however the better integration with the kernel and hardware of LinuxPTP promises better synchronization performance at the cost of some added complexity.

#### Additional Surveyed Vendors
PTP implementations exist both in software and hardware. For comparability reasons, we restrict ourselves to pure software implementations of PTP. Since typical use-cases that require accurate time-synchronization tend toward industrial applications, many solutions are distributed by vendors commercially and are not publicly available. We surveyed all the remaining publicly available solutions for feasibility of integration, totalling at just three (OpenPTP, PPSi, and TimeBeat). 

OpenPTP (https://github.com/stefanct/openptp) is an Open-Source implementation released in late 2009, that has however not received significant attention, with the last release published more than 10 years ago. The author appears to have since moved on to the commercial XR7 PTP stack, and the project can be considered defunct. We encountered difficulties during our attempt to set up a working copy of OpenPTP and subsequently abandoned efforts as we do not consider this implementation as relevant anymore.

PPSi (https://ohwr.org/project/ppsi) is an implementation of PTP by CERN and targets not only Linux but also embedded scenarios. Compared to OpenPTP, PPSi is in a much more mature state, with maintainers still active at the time of writing (2023). Aside from the PTP client itself, PPSi also ships with useful tools that PTP-Perf leverages for benchmark orchestration. Unfortunately, PPSi has also proven unusable in our evaluation, with the client crashing consistently due to buffer-overruns on our testbed. A bug report has been filed and is now pending.

Timebeat (https://www.timebeat.app) is the most recent addition among our surveyed vendors. While it is not open-source, the binaries are readily-available and a license is comparatively simple to obtain. However, Timebeat also relies on heavy-weight infrastructure (elasticsearch), without which it does not appear to function. Since we do not have an elasticsearch instance available on our testbed, Timebeat had to be excluded from the evaluation.
