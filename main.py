from backend import create_app
from backend.config import load_settings


settings = load_settings()
app = create_app(settings)


if __name__ == "__main__":
    app.run(
        host=settings["app_host"],
        port=settings["app_port"],
        debug=settings["app_debug"],
    )
