import subprocess
import time
import shutil
import os
import platform
import multiprocessing

from sys import argv

pdf_path = argv[1]
out_dir = argv[2]
process_counts = [1, 2, 4, 8, 16, 32, 64]
runs_per_setting = 5

system_info = (
    f"{platform.system()} {platform.release()}, {multiprocessing.cpu_count()} cores"
)

results = []

for n in process_counts:
    times = []
    for _ in range(runs_per_setting):
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir, exist_ok=True)

        start = time.perf_counter()
        subprocess.run(
            ["pdfimgextract", pdf_path, out_dir, str(n), "--overwrite", "--skip-dedup"],
            check=True,
        )
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    avg_time = sum(times) / len(times)
    results.append((n, avg_time))

print("# Benchmark pdfimgextract\n")
print(f"Tested on {system_info}\n")
print("|------------|----------------|")
print("| Processes  | Avg Time (sec) |")
print("|------------|----------------|")

for n, avg in results:
    if n < 10:
        print(f"|  {n}         | {avg:.1f}            |")
    else:
        print(f"|  {n}        | {avg:.1f}            |")

print("|------------|----------------|")
