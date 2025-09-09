"""
Metrics and monitoring for MCP Test Environment
"""

import time
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
import json
from pathlib import Path

from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MetricValue:
    """Individual metric value with timestamp"""

    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics for operations"""

    operation_name: str
    duration: float
    success: bool
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """Collects and manages metrics"""

    def __init__(self, max_metrics_per_type: int = 1000):
        self.max_metrics_per_type = max_metrics_per_type
        self.metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_metrics_per_type)
        )
        self.performance_metrics: deque = deque(maxlen=max_metrics_per_type)
        self._lock = threading.Lock()

    def record_metric(
        self, name: str, value: float, tags: Optional[Dict[str, str]] = None
    ):
        """Record a metric value"""
        with self._lock:
            metric = MetricValue(value=value, timestamp=datetime.now(), tags=tags or {})
            self.metrics[name].append(metric)
            logger.debug(f"Recorded metric {name}: {value}")

    def record_performance(
        self,
        operation: str,
        duration: float,
        success: bool,
        error: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ):
        """Record performance metrics"""
        with self._lock:
            metric = PerformanceMetrics(
                operation_name=operation,
                duration=duration,
                success=success,
                error_message=error,
                tags=tags or {},
            )
            self.performance_metrics.append(metric)
            logger.debug(
                f"Recorded performance for {operation}: {duration:.3f}s, success: {success}"
            )

    def get_metrics_summary(
        self, metric_name: str, window_minutes: int = 60
    ) -> Dict[str, Any]:
        """Get summary statistics for a metric within a time window"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(minutes=window_minutes)

            if metric_name not in self.metrics:
                return {"error": f"Metric {metric_name} not found"}

            recent_metrics = [
                m for m in self.metrics[metric_name] if m.timestamp >= cutoff_time
            ]

            if not recent_metrics:
                return {"count": 0, "window_minutes": window_minutes}

            values = [m.value for m in recent_metrics]

            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "window_minutes": window_minutes,
                "latest": values[-1] if values else None,
            }

    def get_performance_summary(
        self, operation: Optional[str] = None, window_minutes: int = 60
    ) -> Dict[str, Any]:
        """Get performance summary for operations"""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(minutes=window_minutes)

            recent_metrics = [
                m for m in self.performance_metrics if m.timestamp >= cutoff_time
            ]

            if operation:
                recent_metrics = [
                    m for m in recent_metrics if m.operation_name == operation
                ]

            if not recent_metrics:
                return {"count": 0, "window_minutes": window_minutes}

            durations = [m.duration for m in recent_metrics]
            success_count = sum(1 for m in recent_metrics if m.success)

            return {
                "count": len(recent_metrics),
                "success_rate": (
                    success_count / len(recent_metrics) if recent_metrics else 0
                ),
                "avg_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "window_minutes": window_minutes,
                "operation": operation,
            }

    def export_metrics(self, file_path: str):
        """Export metrics to JSON file"""
        with self._lock:
            data = {
                "timestamp": datetime.now().isoformat(),
                "metrics": {},
                "performance_metrics": [],
            }

            # Export regular metrics
            for name, metric_deque in self.metrics.items():
                data["metrics"][name] = [
                    {
                        "value": m.value,
                        "timestamp": m.timestamp.isoformat(),
                        "tags": m.tags,
                    }
                    for m in metric_deque
                ]

            # Export performance metrics
            data["performance_metrics"] = [
                {
                    "operation": m.operation_name,
                    "duration": m.duration,
                    "success": m.success,
                    "error": m.error_message,
                    "timestamp": m.timestamp.isoformat(),
                    "tags": m.tags,
                }
                for m in self.performance_metrics
            ]

            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Metrics exported to {file_path}")


class PerformanceTimer:
    """Context manager for timing operations"""

    def __init__(
        self,
        metrics_collector: MetricsCollector,
        operation_name: str,
        tags: Optional[Dict[str, str]] = None,
    ):
        self.metrics_collector = metrics_collector
        self.operation_name = operation_name
        self.tags = tags or {}
        self.start_time = None
        self.success = True
        self.error_message = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.success = False
            self.error_message = str(exc_val)

        duration = time.time() - self.start_time
        self.metrics_collector.record_performance(
            self.operation_name, duration, self.success, self.error_message, self.tags
        )


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector"""
    return _metrics_collector


def record_metric(name: str, value: float, tags: Optional[Dict[str, str]] = None):
    """Convenience function to record a metric"""
    _metrics_collector.record_metric(name, value, tags)


def time_operation(operation_name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator/context manager for timing operations"""
    return PerformanceTimer(_metrics_collector, operation_name, tags)
