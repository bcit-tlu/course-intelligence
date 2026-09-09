"""Quick entry point for running the processor pipeline, API, or worker."""

import logging
import sys

from course_intelligence.default_config import DEFAULT_CONFIG
from course_intelligence.engine import CourseProcessorGraph


def run_api():
    """Start the FastAPI server."""
    import uvicorn

    uvicorn.run(
        "course_intelligence.api:app",
        host=DEFAULT_CONFIG["api_host"],
        port=DEFAULT_CONFIG["api_port"],
        reload=DEFAULT_CONFIG["dev_reload"],
    )


def run_worker():
    """Start the background worker that processes jobs from Redis."""
    from course_intelligence.worker import run

    run()


def run_gateway():
    """Start the LLM gateway proxy service."""
    import os
    import uvicorn

    port = int(os.environ.get("GATEWAY_PORT", "8100"))
    uvicorn.run(
        "course_intelligence.llm.gateway:app",
        host="0.0.0.0",
        port=port,
        reload=DEFAULT_CONFIG["dev_reload"],
    )


def run_pipeline(source_path: str, learning_objectives: str = ""):
    """Run the pipeline on a single file and print results."""
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    graph = CourseProcessorGraph(config=DEFAULT_CONFIG, debug=True)
    result = graph.process(source_path, learning_objectives)

    print(f"\n--- Results ---")
    print(f"Chunks: {len(result.get('knowledge_map', []))}")
    for chunk in result.get("knowledge_map", []):
        print(f"  [{chunk['chunk_id']}] {chunk['topic']}")


if __name__ == "__main__":
    argv = sys.argv[1:]
    learning_objectives = ""
    if "--learning-objectives" in argv:
        i = argv.index("--learning-objectives")
        if i + 1 < len(argv):
            learning_objectives = argv.pop(i + 1)
        argv.pop(i)

    if argv and argv[0] == "api":
        run_api()
    elif argv and argv[0] == "worker":
        run_worker()
    elif argv and argv[0] == "gateway":
        run_gateway()
    elif argv:
        run_pipeline(argv[0], learning_objectives)
    else:
        print("Usage:")
        print("  python main.py api              # Start the FastAPI server")
        print("  python main.py worker           # Start the background worker")
        print("  python main.py gateway          # Start the LLM gateway")
        print("  python main.py <file.pdf|txt> [--learning-objectives '...']   # Process a single file")
