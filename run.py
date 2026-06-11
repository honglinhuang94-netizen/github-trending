"""一键启动脚本

直接运行: python run.py
默认监听 0.0.0.0:8000,浏览器访问 http://localhost:8000
"""
import uvicorn


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
