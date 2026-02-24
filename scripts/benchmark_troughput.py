import os
import time
import statistics
import randomrad as rr


def bench_once(nbytes: int, reps: int) -> dict:
    """
        Measure execution time for rr.randbytes(nbytes) over multiple repetitions.

        Parameters:
            nbytes: Number of bytes requested per call.
            reps:   Number of repetitions.

        Returns:
            Dictionary containing:
                - median_s: Median execution time (seconds)
                - p95_s:    95th percentile execution time (seconds)
                - mb_s_median: Throughput in MB/s based on median
    """
    times = []
    # Repeat the measurement multiple times to reduce noise
    for _ in range(reps):
        t0 = time.perf_counter() # High-resolution timer
        rr.randbytes(nbytes)
        times.append(time.perf_counter() - t0)

    # Sort times to compute percentile
    times_sorted = sorted(times)
    # Median is more stable than average for performance metrics
    median = statistics.median(times)
    # 95th percentile gives insight into tail latency
    p95 = times_sorted[int(0.95 * (reps - 1))]

    return {
        "nbytes": nbytes,
        "reps": reps,
        "median_s": median,
        "p95_s": p95,
        # Convert bytes/second to MB/s using median runtime
        "mb_s_median": (nbytes / (1024 * 1024)) / median,
    }


def main():
    """
        Run two benchmark categories:

        1) Latency tests:
           Small byte requests to measure per-call overhead.

        2) Throughput tests:
           Large byte requests to measure sustained bandwidth.
        """
    print("Backend:", rr.current_backend())
    print("Port:", os.environ.get("RANDOMRAD_PORT"))
    print()

    # -----------------------------
    # Latency-focused measurements
    # -----------------------------
    # Small requests reveal:
    # - Serial roundtrip overhead
    # - Python call overhead
    # - Chunk setup cost
    print("---- Latency tests ----")
    for n in [1, 8, 32, 256, 2048]:
        r = bench_once(n, reps=50)
        print(r)

    print()
    # -----------------------------
    # Throughput-focused measurements
    # -----------------------------
    # Large requests reveal:
    # - Sustained serial bandwidth
    # - Chunk efficiency
    # - Whitening performance cost
    print("---- Throughput tests ----")
    for n in [64 * 1024, 256 * 1024, 1024 * 1024]:
        r = bench_once(n, reps=10)
        print(r)


if __name__ == "__main__":
    main()