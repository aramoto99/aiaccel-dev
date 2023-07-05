import numpy as np
from aiaccel.aiaccel_run import Run


def main(p):
    x = np.array([p["x1"], p["x2"], p["x3"], p["x4"], p["x5"]])
    y = -np.sum(x * np.sin(np.sqrt(np.abs(x))))
    return float(y)


if __name__ == "__main__":
    run = Run()
    run.execute_and_report(main)
