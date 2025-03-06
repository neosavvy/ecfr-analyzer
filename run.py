import uvicorn
import os
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Run the eCFR Analyzer API")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    parser.add_argument("--workers", type=int, default=4, help="Number of worker processes")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="info", 
                        choices=["trace", "debug", "info", "warning", "error", "critical"],
                        help="Log level")
    parser.add_argument("--timeout", type=int, default=600, 
                        help="Timeout for keeping alive connections (seconds)")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    # Set environment variable for custom log level
    if args.log_level.upper() == "TRACE":
        os.environ["LOG_LEVEL"] = "TRACE"
    else:
        os.environ["LOG_LEVEL"] = args.log_level.upper()
    
    # Configure Uvicorn
    config = {
        "app": "app.main:app",
        "host": args.host,
        "port": args.port,
        "workers": args.workers,
        "reload": args.reload,
        "log_level": args.log_level.lower(),
        "timeout_keep_alive": args.timeout,
        # Increase these timeouts for long-running background tasks
        "timeout_graceful_shutdown": 300,  # 5 minutes for graceful shutdown
        "limit_concurrency": 100,  # Allow more concurrent connections
        "backlog": 2048,  # Increase connection queue size
    }
    
    print(f"Starting server with configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    uvicorn.run(**config) 