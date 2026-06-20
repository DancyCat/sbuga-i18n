import warnings


def ignore_pydantic_serialization_userwarning(
    message, category, filename, lineno, file=None, line=None
):
    if category is UserWarning and "PydanticSerializationUnexpectedValue" in str(
        message
    ):
        return
    warnings.showwarning_orig(message, category, filename, lineno, file, line)


warnings.showwarning_orig = warnings.showwarning
warnings.showwarning = ignore_pydantic_serialization_userwarning


def _run_data_worker(api_url: str, port: int, config_path: str):
    from helpers.config_loader import set_config_path

    set_config_path(config_path)
    from data_worker import start_data_worker

    start_data_worker(api_url=api_url, port=port)


if __name__ == "__main__":
    import argparse
    import multiprocessing
    import os
    import time

    parser = argparse.ArgumentParser(description="Sbuga Sonolus Server")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="config.yml",
        help="Path to config file (default: config.yml)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Config file not found: {args.config}")
        raise SystemExit(1)

    os.environ["CONFIG_PATH"] = args.config

    from helpers.config_loader import set_config_path, get_config

    set_config_path(args.config)
    config = get_config()

    api_url = config["api"]["url"]
    data_worker_port = config["server"]["data-worker-port"]

    worker = multiprocessing.Process(
        target=_run_data_worker,
        args=(api_url, data_worker_port, args.config),
        daemon=True,
    )
    worker.start()

    import urllib.request

    for _ in range(30):
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{data_worker_port}/versions"
            ) as resp:
                if resp.status == 200:
                    print("[Main] Data worker is up.")
                    break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        print("[Main] WARNING: Data worker not responding, continuing anyway.")

    import signal
    import atexit

    def _cleanup():
        if worker.is_alive():
            worker.terminate()
            worker.join(timeout=3)
            if worker.is_alive():
                worker.kill()

    atexit.register(_cleanup)

    def _sigint(*_):
        _cleanup()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _sigint)

    from app import start_fastapi

    start_fastapi()
