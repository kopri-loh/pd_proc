from pathlib import Path


# Set-up local (and temporary) sys.path for import
# All scripts for calculations and plots need this
from context import add_path


add_path(Path(".").resolve())

try:
    import lib.io
    import lib.param
    import lib.conv
except Exception:
    raise Exception("Issue with dynamic import")

try:
    from cdp2_post import process_cdp
except Exception:
    raise Exception("Issue with dynamic import")


def test():
    src_path = Path("/home/loh/Storage/CDP2")

    # Path to CDP2 dataset
    src_p = sorted(src_path.glob("2022*"))[0]

    csv_list = sorted(Path(src_p).rglob("*.csv"))

    df_cdp2 = lib.io.read_cdp(csv_list)

    if len(df_cdp2) == 0:
        print("No record found")
        return

    params = lib.param.get_params(csv_list)

    df = process_cdp(df_cdp2, params)
    print(df)
    print(df.columns)


if __name__ == "__main__":
    test()
