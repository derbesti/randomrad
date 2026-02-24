import randomrad as rr
from collections import Counter

def sample_uniform_0_99(n: int) -> list[int]:
    out = []
    while len(out) < n:
        b = rr.randbytes(4096)
        for x in b:
            if x < 200:            # unbiased for mod 100
                out.append(x % 100)
                if len(out) >= n:
                    break
    return out

def main():
    n = 100000
    vals = sample_uniform_0_99(n)
    c = Counter(vals)
    # simple print
    for i in range(100):
        print(i, c[i])

if __name__ == "__main__":
    main()