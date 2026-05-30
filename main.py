import logging

from backend import create_app
from backend.config import load_settings


settings = load_settings()
app = create_app(settings)


def print_startup_url(host, port):
    display_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    print("盲人辅助系统已启动：")
    print("http://{0}:{1}/".format(display_host, port), flush=True)


if __name__ == "__main__":
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    print_startup_url(settings["app_host"], settings["app_port"])
    app.run(
        host=settings["app_host"],
        port=settings["app_port"],
        debug=settings["app_debug"],
        use_reloader=False,
    )
