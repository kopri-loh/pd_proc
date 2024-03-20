import click

from pathlib import Path
from context import add_path


add_path(Path(".").resolve())

try:
    import lib.io
    import lib.param
    import lib.conv
except Exception:
    raise Exception("Issue with dynamic import")

try:
    import post_cdp2
    import post_bcpd
except Exception:
    raise Exception("Issue with dynamic import")


def test():
    src_path = Path("/home/loh/Storage/CDP2")

    # Sample dataset with both valid CDP2 and BCPD output files
    # Change as necessary
    src_p = src_path / "20230225"
    csv_list = sorted(Path(src_p).rglob("*.csv"))

    df_cdp2, par_cdp2 = lib.io.read_cdp2(csv_list)
    df_pbp, df_bcpd, par_bcpd = lib.io.read_bcpd(csv_list)

    print(post_cdp2.process(df_cdp2, par_cdp2))
    print(post_bcpd.process(df_pbp, df_bcpd, par_bcpd))


if __name__ == "__main__":
    test()
