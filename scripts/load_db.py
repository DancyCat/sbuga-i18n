import argparse
import subprocess
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from helpers.config_loader import set_config_path, get_config

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", default="config.yml")
parser.add_argument("-i", "--input", default="sbuga_sonolus_dump.sql")
args = parser.parse_args()

set_config_path(args.config)
psql = get_config()["psql"]
env = {**os.environ, "PGPASSWORD": psql["password"]}
base = ["-h", psql["host"], "-p", str(psql["port"]), "-U", psql["user"]]

result = subprocess.run(
    [
        "psql",
        *base,
        "-tc",
        f"SELECT 1 FROM pg_database WHERE datname = '{psql['database']}'",
    ],
    env=env,
    capture_output=True,
    text=True,
)
if "1" not in result.stdout:
    subprocess.run(
        ["psql", *base, "-c", f"CREATE DATABASE {psql['database']}"],
        env=env,
        check=True,
    )

subprocess.run(
    [
        "pg_restore",
        *base,
        "-d",
        psql["database"],
        "--clean",
        "--if-exists",
        args.input,
    ],
    env=env,
    check=True,
)

print(f"loaded from {args.input}")
