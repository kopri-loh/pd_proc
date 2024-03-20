import numpy as np
import re

from pathlib import Path


def get_buf(buf):
    params = {}

    for _, x in enumerate(buf[1:24]):
        key, val = x.rstrip().split("=")

        if key in ["Sizes", "Thresholds"]:
            val = np.fromstring(re.sub("<[0-9]+>", "", val), dtype=np.int64, sep=",")

        params[key] = val

    return params


def get_params(csv_list):
    # Retrieve instrument parameters
    for item in csv_list:
        item = Path(item)

        print(item.name)

        f_params = ""
        if pd_type == "CDP2":
            if re.search(r"(\d+\s*)CDP(\s*\w+\s*).csv", item.name) is not None:
                f_params = item
        elif pd_type == "BCPD":
            if re.search(r"(\w+\s*)BCPD Beta(\s*\w+)", item.name) is not None:
                f_params = item
        else:
            raise ValueError("Invalid instrument type")

    if f_params == "":
        raise ValueError("Parameters cannot be retrieved")

    with open(f_params) as f:
        return get_buf(f.readlines())
