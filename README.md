# python-pdfimgextract

## 🚀 Overview

**python-pdfimgextract** is a high-performance PDF image extraction tool designed to maximize throughput through multiprocessing.

The project focuses on **speed, reliability, and efficient parallel processing**, enabling large PDFs with hundreds of high-resolution images to be processed significantly faster than traditional single-threaded approaches.

---

## ✨ Features

| Feature | Description |
|-------|-------------|
| ⚡ Parallel Extraction | Utilizes multiprocessing to decode images across multiple CPU cores |
| 🛡️ Atomic Writes | Prevents partially written files during crashes |
| 🧹 Deduplication | Optional removal of identical images |
| 📊 Progress Tracking | Real-time progress bar during extraction |
| 🛑 Graceful Interrupts | Safe handling of SIGINT and termination signals |
| 💻 Clean CLI | Simple command-line interface |

---

## 📥 Installation

```bash
pip install pdfimgextract
```

---

## 🛠️ Usage

Basic usage:

```bash
pdfimgextract INPUT_PDF OUTPUT_DIR NUMBER_OF_PROCESSES
```

Example:

```bash
pdfimgextract manga.pdf output 16
```

Optional flags:

```
-i / --input
-o / --output
-p / --parallelism
```

If the number of processes is not specified, the tool defaults to **8 worker processes**.

---

## 📊 Performance Benchmark

To evaluate the scalability of the multiprocessing implementation, a benchmark was conducted using a large, high-resolution PDF.

### 🖥️ Test Environment

• **OS**: Windows 11  
• **CPU**: 28 Cores  
• **Input File**: 491 MB PDF (514.956.001 bytes)  
• **Extracted Images**: 230 images  
• **Image Size Range**: ~2MB – 10MB

### Benchmark Results

| Proc | Avg (s) | Median | Std Dev | RAM (MB) | Speedup | Eff. |
|-----|------|------|------|------|------|------|
| 1  | 111.88 | 111.84 | 0.09 | 349 | 1.00x | 100% |
| 2  | 56.98  | 57.06  | 0.34 | 626 | 1.96x | 98% |
| 4  | 32.41  | 32.49  | 0.12 | 1159 | 3.45x | 86% |
| 8  | 20.16  | 20.17  | 0.04 | 2254 | 5.55x | 69% |
| 16 | 14.24  | 14.28  | 0.08 | 4423 | 7.86x | 49% |
| 32 | 11.41 | 11.41 | 0.03 | 7309 | 9.81x | 31% |
| 64 | 11.67 | 11.67 | 0.06 | 9306 | 9.59x | 15% |

---

## 📈 Performance Analysis

### Scaling Behavior

The benchmark shows **near-linear scaling at low process counts**, followed by a performance plateau as system limits are reached.

### Near-linear Speedup (1 → 2 processes)

Execution time drops from:

```
111.88s → 56.98s
```

Efficiency:

```
98.2%
```

This indicates that the multiprocessing overhead (process creation, IPC, scheduling) is extremely small relative to the workload.

---

### Peak Throughput

The fastest execution time occurs at **32 processes**:

```
11.41 seconds
Speedup: 9.81x
```

At this point, CPU resources are almost fully saturated and the workload is maximally parallelized.

Beyond this point, performance gains disappear due to system-level constraints.

---

### CPU Oversubscription

Running **64 processes on a 28-core CPU** causes a slight performance regression:

```
11.41s → 11.67s
```

This occurs due to:

- Increased **context switching**
- OS scheduler overhead
- Reduced cache locality
- Worker contention for shared resources

When the number of active processes exceeds the number of physical cores, the operating system must constantly swap running tasks, reducing overall efficiency.

---

## ⚙️ Efficiency Analysis

Efficiency is defined as:

```
Efficiency = Speedup / Number of Processes
```

It measures how effectively each additional CPU contributes to performance.

Observed efficiency:

| Processes | Efficiency |
|----------|-----------|
| 2 | 98.2% |
| 4 | 86.3% |
| 8 | 69.4% |
| 16 | 49.1% |
| 32 | 30.7% |
| 64 | 15.0% |

This decline is expected and is explained by **Amdahl's Law**.

---

## 💽 I/O Bottlenecks

Although image extraction itself is largely CPU-bound, writing **230 large images (2–10MB)** to disk introduces an additional bottleneck.

When many workers attempt to write simultaneously:

- Disk write buffers become saturated
- I/O queue latency increases
- Workers stall waiting for filesystem operations

This explains why increasing processes beyond ~32 yields no additional speedup.

---

## 🏁 Final Performance Summary

| Metric | Value |
|------|------|
| Baseline (1 process) | 111.88s |
| Best Runtime | 11.41s |
| Maximum Speedup | **9.81x** |
| Peak Efficiency | **98.2%** |
| Optimal Range | **8 – 16 processes** |

---

## 🚀 Conclusion

The benchmark results demonstrate that **python-pdfimgextract effectively transforms a heavy serial workload into a scalable parallel pipeline**.

By leveraging multiprocessing and efficient I/O handling, the tool achieves:

- **~10x performance improvement**
- High CPU utilization
- Predictable scaling behavior

This makes it well-suited for processing **large PDFs containing hundreds of high-resolution images**.