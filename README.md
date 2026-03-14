# python-pdfimgextract

## 🚀 python-pdfimgextract

A high-performance, parallel PDF image extractor built for speed and reliability.

## ✨ Features
• ⚡ Parallel Extraction: Fully utilizes multi-core processors for maximum throughput.
• 🛡️ Atomic Writes: Ensures file integrity by preventing partial or corrupted writes.
• 🧹 Deduplication: Automatically identifies and removes duplicate images.
• 💻 Clean CLI: Simple and intuitive command-line interface.
• 📊 Progress Tracking: Real-time visual feedback via a progress bar.
• 🛑 Safe Interruption: Handles signals gracefully to stop without leaving a mess.

## 📥 Installation

```bash
# Clone the repository
git clone https://github.com/your-username/python-pdfimgextract

# Navigate to the directory
cd python-pdfimgextract

# Install the package and dependencies
pip install .
```

## 🛠️ Usage

```bash
pdfimgextract [INPUT_PDF] [OUTPUT_DIR] [NUMBER_OF_PROCESSES]
```

Or use the optional flags:

--input | -i  
--output | -o  
--parallelism | -p  

The default number of parallel processes is **8** if not specified.

## 📊 Performance & Benchmarking

Performance Benchmark

To evaluate the efficiency of the multiprocessing implementation, a stress test was conducted using a high-resolution PDF document.

💻 Test Environment:

OS: Windows 11

CPU: 28 Cores

Input File: 491 MB PDF (514,956,001 bytes)

Extracted result: 230 images (ranging from ~2MB to 10MB each)

![Benchmark](./docs/assets/benchmark.png)

📈 Key Observations:

• Linear Scaling (Low Core Count): The transition from 1 to 2 processes is nearly perfect (99% efficiency), demonstrating minimal initial overhead.

• Sub-linear Scaling: From 4 to 16 processes, we see a steady increase in speed, but the Speedup ($S$) starts to lag behind the core count due to resource contention.

• Hardware Saturation: On this 28-core machine, performance peaks at 32 processes (11.3s). Beyond this point (64 processes), the execution time actually increases to 11.6s due to Context Switching and CPU over-provisioning.

## ⚡ Efficiency

Efficiency & Scalability Analysis

While Speedup $(S)$ measures the reduction in execution time, Efficiency $(E)$ measures how effectively each additional CPU worker is utilized.

Performance Data

![Efficiency](./docs/assets/efficiency.png)

🔍 Analysis: 

• Parallel Overhead: As the process count increases, the time spent on process synchronization and task distribution begins to consume a larger share of the total execution time. This is reflected in the drop from 99% efficiency (2 cores) to 31.6% efficiency (32 cores).

• I/O Bottlenecks: PDF image extraction is a hybrid task. While the decoding is CPU-bound, the final writing of 230 high-res images is Disk I/O bound. Once the storage throughput is saturated, adding more CPU processes offers no further benefit.

• The "Sweet Spot": For this hardware configuration, 8 to 16 processes represent the optimal balance. In this range, the system achieves a significant speedup (up to 7.88x) while maintaining a reasonable resource-to-performance ratio.

• Negative Returns: At 64 processes, efficiency drops to 15.4%. Running more processes than physical cores available (28) leads to "Thrashing," where the OS spends more time swapping tasks than actually processing data.

## 🏆 Final Verdict Summary
The benchmarks demonstrate that pdfimgextract significantly reduces processing time through effective parallelization. While the implementation scales exceptionally well up to the physical core limit of the hardware, the transition from 114.3s (Single-core) to 11.3s (Multi-core) represents a 10x performance increase.

🚀 Recommendation

For most high-resolution extraction tasks:
• For Efficiency: Use a process count equal to half of your available logical cores.
• For Raw Speed: Match the process count to your total physical cores ($N$).
• Avoid Over-provisioning: Setting processes beyond your hardware thread count (e.g., 64 on a 28-core system) will degrade performance due to I/O saturation and context switching.

🛠️ Key Takeaways
• Max Speedup: $10.12x$
• Peak Efficiency: $99\%$ (at 2 processes)
• Optimal Range: $8 - 20$ processes