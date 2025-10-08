"""
Performance benchmark suite for QGIS MCP Server

This package contains comprehensive performance benchmarks testing:
- Protocol handling (BufferedProtocolHandler vs naive parsing)
- Cache performance (GeometryCache hit rates and speedup)
- Feature access optimization (spatial index, pagination, etc.)
- Async operations (threading overhead, concurrency)
- End-to-end workflows (realistic usage scenarios)

Run all benchmarks:
    python run_all_benchmarks.py

Run individual benchmarks:
    python benchmark_protocol.py
    python benchmark_cache.py
    python benchmark_features.py
    python benchmark_async.py
    python benchmark_end_to_end.py
"""

__version__ = '1.0.0'
