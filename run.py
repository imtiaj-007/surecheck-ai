import os

import uvicorn


def run_server() -> None:
    """
    Programmatic entry point for running the FastAPI server.
    """
    is_production = os.getenv("APP_ENV", "development") == "production"

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    log_level = os.getenv("LOG_LEVEL", "info" if is_production else "debug")

    reload = not is_production
    use_colors = False if is_production else True
    workers = 4 if is_production else 1

    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level=log_level,
        use_colors=use_colors,
    )


if __name__ == "__main__":
    run_server()
