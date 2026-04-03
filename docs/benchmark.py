import subprocess
import time
import platform
import shutil
import psutil
import os
import sys

from statistics import mean, median, stdev
from tqdm import tqdm

# Configuration and CLI arguments
PDF_PATH = sys.argv[1]
OUTPUT_DIR = sys.argv[2] if len(sys.argv) > 2 else "./benchmark_output"

PROCESS_COUNTS = [1, 2, 4, 8, 16, 32]
RUNS = 5

# Precompute input size for throughput calculation (MB)
FILE_SIZE_MB = os.path.getsize(PDF_PATH) / (1024**2)


# =========================
# System Information
# =========================


def get_cpu_info():
    """
    Retrieve CPU model name and hardware concurrency (Physical/Logical).

    Queries PowerShell on Windows and /proc/cpuinfo on Linux.
    """
    cpu = platform.processor()

    if not cpu:
        try:
            if platform.system() == "Windows":
                # Use CIM instance for detailed hardware name
                cpu = (
                    subprocess.check_output(
                        [
                            "powershell",
                            "-Command",
                            "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name",
                        ],
                        stderr=subprocess.DEVNULL,
                    )
                    .decode()
                    .strip()
                )

            elif platform.system() == "Linux":
                # Parse model name from cpuinfo
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "model name" in line:
                            cpu = line.split(":", 1)[1].strip()
                            break

        except Exception:
            cpu = "Unknown CPU"

    physical = psutil.cpu_count(logical=False)
    logical = psutil.cpu_count(logical=True)

    return f"{cpu} ({physical}C/{logical}T)"


def get_ram_info():
    """Return total installed system RAM in gigabytes."""
    ram = psutil.virtual_memory().total / (1024**3)
    return f"{ram:.1f} GB"


def get_os_info():
    """Return OS distribution/version with kernel/build details."""
    system = platform.system()

    if system == "Windows":
        return f"{system} {platform.release()} (Build {platform.version()})"

    elif system == "Linux":
        try:
            # Prefer pretty name from os-release
            with open("/etc/os-release") as f:
                data = dict(line.strip().split("=", 1) for line in f if "=" in line)
            name = data.get("PRETTY_NAME", "Linux")
            return name.strip('"')
        except Exception:
            return f"Linux ({platform.release()})"

    return f"{system} {platform.release()}"


def get_disk_info():
    """Retrieve primary storage device model via system CLI."""
    try:
        system = platform.system()

        if system == "Windows":
            disks = (
                subprocess.check_output(
                    [
                        "powershell",
                        "-Command",
                        "Get-PhysicalDisk | Select-Object -ExpandProperty FriendlyName",
                    ],
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .splitlines()
            )

            disks = [d.strip() for d in disks if d.strip()]
            return disks[0] if disks else "Unknown disk"

        elif system == "Linux":
            disks = (
                subprocess.check_output(
                    ["lsblk", "-d", "-o", "MODEL"],
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .splitlines()
            )

            disks = [d.strip() for d in disks if d.strip() and d != "MODEL"]
            return disks[0] if disks else "Unknown disk"

        return "Disk info unavailable"

    except Exception:
        return "Unknown disk"


def print_system_info():
    """Log hardware and software environment metadata."""
    print("# Benchmark pdfimgextract\n")
    print("## System Info\n")
    print(f"- CPU: {get_cpu_info()}")
    print(f"- RAM: {get_ram_info()}")
    print(f"- OS: {get_os_info()}")
    print(f"- Disk: {get_disk_info()}\n")


# =========================
# Memory Tracking
# =========================


def get_tree_memory(proc):
    """
    Calculate total Resident Set Size (RSS) for a process and all its descendants.

    :param proc: psutil.Process instance
    :return: Memory usage in MB
    """
    mem = 0

    try:
        mem += proc.memory_info().rss
        for child in proc.children(recursive=True):
            try:
                mem += child.memory_info().rss
            except psutil.NoSuchProcess:
                pass
    except psutil.NoSuchProcess:
        pass

    return mem / (1024 * 1024)


# =========================
# Benchmark Execution
# =========================


def run_once(processes: int):
    """
    Execute the target binary and monitor its resource consumption.

    :param processes: Thread/Process count passed to the binary
    :return: Tuple of (elapsed_time, peak_memory_mb)
    """
    # Clean output directory to avoid I/O interference or caching
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    ram_peak = 0
    start = time.perf_counter()

    # Launch subprocess with suppressed pipes
    proc = subprocess.Popen(
        ["pdfimgextract", PDF_PATH, OUTPUT_DIR, str(processes)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    p = psutil.Process(proc.pid)

    # Poll process state and sample memory usage
    while proc.poll() is None:
        time.sleep(0.1)
        ram_peak = max(ram_peak, get_tree_memory(p))

    elapsed = time.perf_counter() - start

    return elapsed, ram_peak


def benchmark():
    """
    Run the benchmark suite across defined process counts.

    Calculates Parallel Speedup, Efficiency, and Throughput.
    """
    results = []
    baseline = None

    total_runs = len(PROCESS_COUNTS) * RUNS

    with tqdm(
        total=total_runs,
        desc="Benchmark",
        colour="green",
        dynamic_ncols=True,
        bar_format="{l_bar}{bar} {n_fmt}/{total_fmt} [{unit}]",
    ) as pbar:
        for p in PROCESS_COUNTS:
            runs = []
            for i in range(RUNS):
                pbar.unit = f"processes={p}, run={i + 1}"
                pbar.refresh()

                result = run_once(p)
                runs.append(result)
                pbar.update(1)

            # Statistical aggregation
            times = [r[0] for r in runs]
            rams = [r[1] for r in runs]
            avg = mean(times)

            # Set baseline for Speedup (S = T1 / Tp)
            if baseline is None:
                baseline = avg

            speedup = baseline / avg
            efficiency = (speedup / p) * 100
            throughput = FILE_SIZE_MB / avg

            results.append(
                (
                    p,
                    avg,
                    median(times),
                    stdev(times) if len(times) > 1 else 0,
                    mean(rams),
                    speedup,
                    efficiency,
                    throughput,
                )
            )

    return results


# =========================
# Output Formatting
# =========================


def print_results(results):
    """Format and print results as a Markdown-compatible table."""

    def safe(val, width, precision=2):
        """Ensure numerical values fit within table column constraints."""
        text = f"{val:.{precision}f}"
        if len(text) > width:
            text = f"{val:.2e}"
        return text.ljust(width)[:width]

    print(
        "|------------|--------------|--------------|-----------|----------|---------|--------------|-----------------|"
    )
    print(
        "| Processes  | Avg (sec)    | Median (sec) | Std Dev   | RAM MB   | Speedup | Efficiency % | Throughput MB/s |"
    )
    print(
        "|------------|--------------|--------------|-----------|----------|---------|--------------|-----------------|"
    )

    for p, avg, med, sd, ram, sp, eff, thr in results:
        print(
            f"|{str(p).ljust(12)}"
            f"|{safe(avg,14)}"
            f"|{safe(med,14)}"
            f"|{safe(sd,11)}"
            f"|{safe(ram,10)}"
            f"|{safe(sp,9)}"
            f"|{safe(eff,14)}"
            f"|{safe(thr,17)}|"
        )

    print(
        "|------------|--------------|--------------|-----------|----------|---------|--------------|-----------------|"
    )


# =========================
# Execution Entry Point
# =========================


def main():
    """Main execution flow: Setup -> Benchmark -> Teardown."""
    try:
        print_system_info()
        results = benchmark()
        print_results(results)

    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user.")

    finally:
        # Final cleanup of benchmark artifacts
        if os.path.exists(OUTPUT_DIR):
            shutil.rmtree(OUTPUT_DIR, ignore_errors=True)


if __name__ == "__main__":
    main()
