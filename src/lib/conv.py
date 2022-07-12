import numpy as np


# Define 1D Gaussian kernel
def gauss(x=11, sig=1):
    xx = np.linspace(-(x - 1) / 2, (x - 1) / 2, x)
    kernel = np.exp(-((xx / sig) ** 2) / 2) / (sig * np.sqrt(2 * np.pi))

    return kernel / np.sum(kernel)


# 2D Gaussian kernel, for future use
def gauss2d(x=5, sig=1):
    xx = np.linspace(-(x - 1) / 2, (x - 1) / 2, x)
    kernel = np.exp(-((xx / sig) ** 2) / 2) / (sig * np.sqrt(2 * np.pi))
    kernel = np.outer(kernel, kernel)

    return kernel / np.sum(kernel)


# Wrapper for convolution
def g_cov(arr, x=300, sig=300):
    if np.nansum(arr) == 0:
        return arr

    # Pad input array at boundaries
    _a = np.concatenate((np.zeros(x // 2), arr, np.zeros(x // 2)))

    arr_m = np.nanmean(arr.astype(float))
    arr_sm = np.convolve(
        _a - arr_m,
        gauss(x=x, sig=sig),
        mode="same",
    )[int(x / 2) : int(-x / 2)]

    return arr_sm + arr_m
