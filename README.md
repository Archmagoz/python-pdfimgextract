# 📄 pdfimgextract

A fast and parallelized Python tool for extracting images from PDF files with support for multiprocessing, deduplication, and high-throughput workflows.

---

## 🚀 Features

- ⚡ Multiprocessing-based extraction
- 🧵 Configurable number of worker processes
- 🖼️ Extracts embedded images directly from PDF objects
- 🧹 Optional deduplication of images
- 📦 Preserves original image formats when possible
- 📊 Optimized for high-performance batch processing
- 🪵 Clean output structure for automation pipelines

---

## 📦 Installation

### Requirements

- Python 3.10+

### Install

```bash
pip install pdfimgextract
```

---

## ▶️ Usage

### Basic usage

```bash
pdfimgextract input.pdf output_dir  
```

### Example

```bash
pdfimgextract ./sample.pdf ./output  
```

---

## ⚙️ Options

| Argument | Description |
|----------|------------|
| input.pdf | Path to the input PDF file |
| output_dir | Directory where extracted images will be saved |
| --workers | Number of parallel processes (optional) |
| --overwrite | Overwrite existing files if present |
| --dedup | Enable image deduplication |

---

## 🧵 Parallelism Model

- The tool uses **process-based parallelism (multiprocessing)**
- Each worker processes a portion of the PDF image extraction workload
- Performance scales depending on:
  - CPU core count
  - Disk throughput
  - Memory availability

---

## 📁 Output Structure

Extracted images are saved in the specified output directory.

Example:

output/  
├── 0001.png  
├── 0002.jpg  
├── 0003.png  


---

## 📊 Benchmark

A benchmark was conducted to evaluate scalability and performance under different process counts using the same PDF input.

### 🖥️ System Configuration

- CPU: Intel64 Family 6 Model 183 Stepping 1 (20 cores / 28 threads)
- RAM: 63.8 GB
- OS: Windows 11 (Build 10.0.26200)
- Disk: KINGSTON SA400S37480G (SATA SSD)

---

### ⚙️ Methodology

- Same PDF file used across all tests
- Identical workload for each process configuration
- Multiple runs executed per configuration
- Metrics aggregated:
  - Average time
  - Median
  - Standard deviation
- Process counts tested:
  - 1, 2, 4, 8, 16, 32

📌 The benchmark is fully reproducible and can be validated using the scripts and artifacts available in the `docs/` directory.

---

### 📈 Results

| Processes | Avg (sec) | Median (sec) | Std Dev | RAM MB  | Speedup | Efficiency % | Throughput MB/s |
|----------|-----------|--------------|---------|---------|---------|--------------|-----------------|
| 1        | 112.92    | 112.88       | 0.17    | 355.17  | 1.00    | 100.00       | 4.35            |
| 2        | 58.20     | 58.23        | 0.52    | 637.87  | 1.94    | 97.01        | 8.44            |
| 4        | 33.89     | 33.55        | 0.96    | 1182.90 | 3.33    | 83.29        | 14.49           |
| 8        | 21.80     | 21.04        | 1.17    | 2302.81 | 5.18    | 64.76        | 22.53           |
| 16       | 15.17     | 15.15        | 0.06    | 4506.38 | 7.45    | 46.54        | 32.38           |
| 32       | 11.73     | 11.72        | 0.07    | 7476.22 | 9.63    | 30.09        | 41.88           |

---

### 🧠 Notes on Performance

- Near-linear scaling at low process counts
- Diminishing returns beyond ~8–16 processes
- Performance becomes increasingly constrained by:
  - Disk I/O
  - Process overhead
  - Memory usage
- Best efficiency observed in the 8–16 worker range
- Maximum throughput achieved at 32 workers, with reduced efficiency

---

## 📁 Benchmark Validation

The benchmark can be inspected, executed, and validated directly from the `docs/` directory in this repository.

---

## ⚠️ Limitations

- Performance depends heavily on storage speed (SSD vs NVMe)
- Large PDFs with many embedded images may significantly increase memory usage
- Multiprocessing overhead may reduce efficiency at very high worker counts
- Deduplication may introduce additional computational cost

---

## 📜 License

MIT License (or your chosen license)

---

## 🤝 Contributing

Contributions are welcome.

- Open issues for bugs or suggestions
- Submit pull requests with improvements
- Keep changes consistent with the existing architecture and style