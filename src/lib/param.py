import numpy as np
import re

from pathlib import Path


def get_params(csv_list):
    # Retrieve instrument parameters from CDP2 configuration file
    for item in csv_list:
        item = Path(item)

        if re.search("(\w+\s*)CDP(\s*\w+)", item.name) is not None:
            cdp_file = item

    with open(cdp_file) as f:
        buf = f.readlines()

        params = {}
        for i, x in enumerate(buf[1:24]):
            key, val = x.rstrip().split("=")

            if key in ["Sizes", "Thresholds"]:
                val = np.fromstring(
                    re.sub("<[0-9]+>", "", val), dtype=np.int64, sep=","
                )

            params[key] = val

    return params
