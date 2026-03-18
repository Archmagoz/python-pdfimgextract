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

Optional usage (flags):

```bash
pdfimgextract -i input.pdf -o output_dir -p 8
pdfimgextract -i input.pdf -o output_dir -d hash
pdfimgextract -i input.pdf -o output_dir --overwrite
```

### Arguments

```
-i / --input         Path to input PDF
-o / --output        Output directory
-p / --parallelism   Number of worker processes (default: 8)
-d / --dedup         Deduplication method: xref (default) or hash (precise but slower)
--overwrite          Overwrite existing files
```

If not specified, the tool defaults to:
- **8 workers**
- **xref deduplication**

---

## 📊 Performance & Benchmark

### 🖥️ Test Environment

• **OS**: Windows 11  
• **CPU**: 28 cores  
• **Input File**: 491 MB PDF  
• **Extracted Images**: 230  
• **Image Size Range**: ~2MB – 10MB  

---

### 📈 Results

| Proc | Time (s) | Speedup | Efficiency | RAM (MB) |
|------|---------|--------|-----------|---------|
| 1  | 111.88 | 1.00x | 100% | 349 |
| 2  | 56.98  | 1.96x | 98%  | 626 |
| 4  | 32.41  | 3.45x | 86%  | 1159 |
| 8  | 20.16  | 5.55x | 69%  | 2254 |
| 16 | 14.24  | 7.86x | 49%  | 4423 |
| 32 | 11.41  | 9.81x | 31%  | 7309 |
| 64 | 11.67  | 9.59x | 15%  | 9306 |

---

### 🧠 Analysis

**Scaling**
- Near-linear scaling up to ~4 processes  
- Strong gains up to ~16  
- Performance plateaus around ~32  

**CPU Efficiency**
- Very high at low parallelism (~98% at 2 workers)  
- Gradual drop due to scheduling and contention  
- Diminishing returns at 64 and beyond workers  

**Memory Usage**
- RAM scales almost linearly with process count  
- Each worker holds its own decoding state  
- Large images amplify memory consumption  

Examples:
- 8 workers → ~2.2 GB  
- 32 workers → ~7.3 GB  
- 64 workers → ~9.3 GB  

**I/O Bottleneck**
- Parallel writes saturate disk bandwidth  
- Causes worker stalls at high process counts  
- Main limiter beyond ~32 workers  

---

### 🏁 Optimal Range

**Recommended configuration:**

```
8 – 16 workers
```

Best balance between:
- Speed
- Efficiency
- Memory usage
- I/O pressure
