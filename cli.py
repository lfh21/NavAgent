import argparse

from backend import create_app
from backend.config import load_settings


def main():
    settings = load_settings()

    parser = argparse.ArgumentParser(description="Blind assist web demo helper CLI")
    subparsers = parser.add_subparsers(dest="command")

    runserver = subparsers.add_parser("runserver", help="启动 Web Demo 服务")
    runserver.add_argument("--host", default=settings["app_host"])
    runserver.add_argument("--port", type=int, default=settings["app_port"])
    runserver.add_argument("--debug", action="store_true", default=settings["app_debug"])

    subparsers.add_parser("show-config", help="输出当前配置")

    args = parser.parse_args()

    if args.command is None:
        args.command = "runserver"
        args.host = settings["app_host"]
        args.port = settings["app_port"]
        args.debug = settings["app_debug"]

    if args.command == "show-config":
        for key, value in settings.items():
            print("{0}={1}".format(key, value))
        return

    app = create_app(settings)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
