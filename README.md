# python-pdfimgextract

A fast parallel PDF image extractor written in Python.

## Features

- parallel extraction
- atomic file writes
- duplicate image removal
- clean CLI interface
- progress bar
- safe interruption handling

## Installation

```bash
git clone this repo
cd python-pdfimgextract
pip install .
```

## Usage

```bash
pdfimgextract [INPUT_PDF] [OUTPUT_DIR] [NUMBER_OF_PROCESSES]
```

Or use the optional flags:

--input | -i  
--output | -o  
--parallelism | -p  

The default number of parallel processes is **8** if not specified.

## Benchmark

Performance Benchmark
To evaluate the efficiency of the multiprocessing implementation, a stress test was conducted using a high-resolution PDF document.

Test Environment:

OS: Windows 11

CPU: 28 Cores

Input File: 491 MB PDF (514,956,001 bytes)

Extracted result: 230 images (ranging from ~2MB to 10MB each)

![Benchmark de Performance](./docs/assets/benchmark.png)

Key Observations:
Scaling: Moving from 4 to 20 processes nearly doubled the extraction speed (1.93x faster).

Diminishing Returns: Between 20 and 40 processes, the performance gain was minimal (~1.3s), suggesting that the bottleneck shifts from CPU processing to Disk I/O or overhead management.

Sweet Spot: For this specific hardware (28 cores), 20 processes offered the best balance between performance and resource allocation.