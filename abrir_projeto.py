import os


def main() -> None:
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))

    print("URLs do projeto FiscalIA Pro:")
    print(f"- App: http://{host}:{port}")
    print(f"- Docs (Swagger): http://{host}:{port}/docs")
    print(f"- Health: http://{host}:{port}/health")


if __name__ == "__main__":
    main()
