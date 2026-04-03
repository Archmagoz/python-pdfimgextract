# 📄 pdfimgextract

**pdfimgextract** is a high-performance, parallelized Python utility designed for extracting images from PDF documents. Engineered for speed and reliability, it leverages multiprocessing to handle high-throughput workflows with built-in support for deduplication and atomic file operations.

---

## ✨ Features

| Feature | Description |
|:---|:---|
| ⚡ **Parallel Extraction** | Scales workloads across multiple CPU cores using process-based parallelism. |
| 🛡️ **Atomic Writes** | Ensures data integrity by preventing partial file corruption during crashes. |
| 🧹 **Deduplication** | Optional removal of redundant images based on `xref` or cryptographic hashing. |
| 📊 **Progress Tracking** | Real-time visual feedback via an integrated progress bar. |
| 🛑 **Graceful Termination** | Cleanly handles `SIGINT` and termination signals to prevent orphaned processes. |
| 💻 **Intuitive CLI** | Streamlined command-line interface for rapid deployment. |

---

## 📦 Installation

### Prerequisites
- **Python 3.10+**

### Install via pip
```bash
pip install pdfimgextract
```

---

## ▶️ Usage

### Basic Command
```bash
pdfimgextract <input.pdf> <output_dir>
```

### Practical Example
```bash
pdfimgextract ./sample.pdf ./output_images
```

---

## ⚙️ Configuration & Options

| Argument | Description |
|:---|:---|
| `input.pdf` | Path to the source PDF file. |
| `output_dir` | Destination directory for extracted assets. |
| `--parallelism X` | Number of concurrent worker processes (defaults to CPU count). |
| `--overwrite` | Force overwrite of existing files in the output directory. |
| `--dedup METHOD` | Enable image deduplication. Supported methods: `xref` (default) or `hash`. |

---

## 🧵 Concurrency Model

The tool implements a **process-based parallelism** model to bypass Python's Global Interpreter Lock (GIL) and maximize CPU utilization:
- Each worker process independently accesses the PDF to extract image streams.
- **Performance Scaling** is determined by:
    - CPU core availability and clock speed.
    - Disk I/O throughput (SATA vs. NVMe).
    - Available System RAM.

---

## 📁 Output Structure

Extracted images are organized sequentially within the target directory:

```text
output/
├── 0001.png
├── 0002.jpg
├── 0003.png
```

---

## 📊 Performance Benchmarks

A comprehensive evaluation was conducted to measure scalability and efficiency across varying process counts.

### 🖥️ Test Environment
- **CPU:** Intel Core (20 Cores / 28 Threads)
- **RAM:** 64 GB
- **OS:** Windows 11
- **Storage:** Kingston SATA SSD

### 📄 Dataset Profile
- **Input:** 491 MB PDF
- **Payload:** 230 Images (Range: 2MB – 10MB per image)

---

### 📈 Results Table

| Processes | Avg (s) | Median (s) | Std Dev | RAM (MB) | Speedup | Efficiency | Throughput |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | 112.92 | 112.88 | 0.17 | 355 | 1.00x | 100.0% | 4.35 MB/s |
| **2** | 58.20 | 58.23 | 0.52 | 637 | 1.94x | 97.0% | 8.44 MB/s |
| **4** | 33.89 | 33.55 | 0.96 | 1,182 | 3.33x | 83.3% | 14.49 MB/s |
| **8** | 21.80 | 21.04 | 1.17 | 2,302 | 5.18x | 64.8% | 22.53 MB/s |
| **16** | 15.17 | 15.15 | 0.06 | 4,506 | 7.45x | 46.5% | 32.38 MB/s |
| **32** | 11.73 | 11.72 | 0.07 | 7,476 | 9.63x | 30.1% | 41.88 MB/s |

---

### 🧠 Performance Insights
- **Linear Scaling:** Observed primarily at lower process counts (1–4 workers).
- **Diminishing Returns:** Gains begin to plateau beyond 16 processes as the bottleneck shifts from CPU to **Disk I/O** and **Process Management Overhead**.
- **Sweet Spot:** Optimal efficiency/resource balance is typically found between **8 and 16 workers** for this hardware configuration.
- **Maximum Throughput:** Peak data processing occurs at 32 workers, albeit at the cost of significantly higher memory consumption and lower per-core efficiency.

---

## 📁 Validation

The benchmarking scripts and raw data are available for inspection and reproduction within the `docs/` directory of this repository.

---

## ⚠️ Limitations
- **Hardware Bound:** Overall speed is heavily contingent on storage latency (NVMe recommended for peak performance).
- **Memory Footprint:** High process counts with large PDFs can lead to substantial RAM usage.
- **Deduplication Overhead:** Enabling `hash`-based deduplication adds a computational layer that may slightly increase processing time.

---

## 🤝 Contributing

Contributions drive improvement! If you encounter bugs or have architectural suggestions, please open an issue or submit a pull request.