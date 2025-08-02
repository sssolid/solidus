# src/core/health.py
"""
Health check views and utilities for monitoring system status
"""
import os
import time

import psutil
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone
from django.views import View

User = get_user_model()


class HealthCheckView(View):
    """
    Comprehensive health check endpoint for monitoring system status
    """

    def get(self, request):
        """Return system health status"""
        start_time = time.time()
        health_data = {
            "status": "healthy",
            "timestamp": timezone.now().isoformat(),
            "version": getattr(settings, "VERSION", "1.0.0"),
            "environment": "production" if not settings.DEBUG else "development",
            "checks": {},
        }

        # Database check
        health_data["checks"]["database"] = self._check_database()

        # Cache check
        health_data["checks"]["cache"] = self._check_cache()

        # Storage check
        health_data["checks"]["storage"] = self._check_storage()

        # System resources check
        health_data["checks"]["system"] = self._check_system_resources()

        # Application metrics
        health_data["checks"]["application"] = self._check_application_metrics()

        # Calculate response time
        health_data["response_time_ms"] = round((time.time() - start_time) * 1000, 2)

        # Determine overall status
        failed_checks = [
            name
            for name, check in health_data["checks"].items()
            if not check["healthy"]
        ]

        if failed_checks:
            health_data["status"] = "unhealthy"
            health_data["failed_checks"] = failed_checks

        # Return appropriate HTTP status
        status_code = 200 if health_data["status"] == "healthy" else 503

        return JsonResponse(health_data, status=status_code)

    def _check_database(self):
        """Check database connectivity and performance"""
        try:
            start_time = time.time()

            # Test basic connectivity
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            # Test a simple query
            user_count = User.objects.count()

            response_time = round((time.time() - start_time) * 1000, 2)

            return {
                "healthy": True,
                "response_time_ms": response_time,
                "user_count": user_count,
                "database_name": connection.settings_dict["NAME"],
            }
        except Exception as e:
            return {"healthy": False, "error": str(e), "response_time_ms": None}

    def _check_cache(self):
        """Check cache system functionality"""
        try:
            start_time = time.time()

            # Test cache write/read
            test_key = "health_check_test"
            test_value = f"test_{int(time.time())}"

            cache.set(test_key, test_value, 60)
            retrieved_value = cache.get(test_key)

            # Clean up
            cache.delete(test_key)

            response_time = round((time.time() - start_time) * 1000, 2)

            if retrieved_value == test_value:
                return {
                    "healthy": True,
                    "response_time_ms": response_time,
                    "backend": cache.__class__.__name__,
                }
            else:
                return {
                    "healthy": False,
                    "error": "Cache read/write test failed",
                    "response_time_ms": response_time,
                }

        except Exception as e:
            return {"healthy": False, "error": str(e), "response_time_ms": None}

    def _check_storage(self):
        """Check file storage accessibility"""
        try:
            import os

            # Check media directory accessibility
            media_path = settings.MEDIA_ROOT
            media_writable = (
                os.access(media_path, os.W_OK) if os.path.exists(media_path) else False
            )

            # Check static files directory
            static_path = getattr(settings, "STATIC_ROOT", None)
            static_exists = os.path.exists(static_path) if static_path else False

            # Get disk usage if possible
            disk_usage = None
            if os.path.exists(media_path):
                try:
                    disk_usage = psutil.disk_usage(media_path)
                    disk_usage = {
                        "total_gb": round(disk_usage.total / (1024**3), 2),
                        "used_gb": round(disk_usage.used / (1024**3), 2),
                        "free_gb": round(disk_usage.free / (1024**3), 2),
                        "percent_used": round(
                            (disk_usage.used / disk_usage.total) * 100, 1
                        ),
                    }
                except Exception as e:
                    import logging

                    logger = logging.getLogger("core.health")
                    logger.error(f"Error in core health: {str(e)}")
                    pass

            return {
                "healthy": media_writable and static_exists,
                "media_writable": media_writable,
                "static_exists": static_exists,
                "disk_usage": disk_usage,
            }

        except Exception as e:
            return {"healthy": False, "error": str(e)}

    def _check_system_resources(self):
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent_used": memory.percent,
            }

            # Disk I/O
            disk_io = psutil.disk_io_counters()
            disk_io_stats = (
                {
                    "read_mb": round(disk_io.read_bytes / (1024**2), 2),
                    "write_mb": round(disk_io.write_bytes / (1024**2), 2),
                }
                if disk_io
                else None
            )

            # Load average (Unix systems only)
            load_avg = None
            try:
                load_avg = os.getloadavg()
            except (OSError, AttributeError):
                pass

            # Determine if resources are healthy
            healthy = cpu_percent < 90 and memory_usage["percent_used"] < 90

            return {
                "healthy": healthy,
                "cpu_percent": cpu_percent,
                "memory": memory_usage,
                "disk_io": disk_io_stats,
                "load_average": load_avg,
            }

        except Exception as e:
            return {"healthy": False, "error": str(e)}

    def _check_application_metrics(self):
        """Check application-specific metrics"""
        try:
            from src.assets.models import Asset
            from src.feeds.models import DataFeed
            from src.products.models import Product

            # Basic counts
            metrics = {
                "total_users": User.objects.count(),
                "active_users": User.objects.filter(is_active=True).count(),
                "total_products": Product.objects.count(),
                "active_products": Product.objects.filter(is_active=True).count(),
                "total_assets": Asset.objects.count(),
                "total_feeds": DataFeed.objects.count(),
                "active_feeds": DataFeed.objects.filter(is_active=True).count(),
            }

            # Recent activity (last 24 hours)
            from datetime import timedelta

            yesterday = timezone.now() - timedelta(days=1)

            metrics.update(
                {
                    "new_users_24h": User.objects.filter(
                        date_joined__gte=yesterday
                    ).count(),
                    "new_assets_24h": Asset.objects.filter(
                        created_at__gte=yesterday
                    ).count(),
                }
            )

            return {"healthy": True, "metrics": metrics}

        except Exception as e:
            return {"healthy": False, "error": str(e)}


class SimpleHealthCheckView(View):
    """
    Simple health check for basic monitoring (faster response)
    """

    def get(self, request):
        """Return basic health status"""
        try:
            # Quick database check
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            return JsonResponse(
                {"status": "healthy", "timestamp": timezone.now().isoformat()}
            )

        except Exception as e:
            return JsonResponse(
                {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": timezone.now().isoformat(),
                },
                status=503,
            )


class ReadinessCheckView(View):
    """
    Readiness check for Kubernetes-style deployments
    """

    def get(self, request):
        """Check if application is ready to serve traffic"""
        try:
            # Check database
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            # Check cache
            cache.set("readiness_test", "ok", 10)
            if cache.get("readiness_test") != "ok":
                raise Exception("Cache not working")
            cache.delete("readiness_test")

            return JsonResponse(
                {"status": "ready", "timestamp": timezone.now().isoformat()}
            )

        except Exception as e:
            return JsonResponse(
                {
                    "status": "not_ready",
                    "error": str(e),
                    "timestamp": timezone.now().isoformat(),
                },
                status=503,
            )


class LivenessCheckView(View):
    """
    Liveness check for Kubernetes-style deployments
    """

    def get(self, request):
        """Check if application is alive (basic functionality)"""
        return JsonResponse(
            {
                "status": "alive",
                "timestamp": timezone.now().isoformat(),
                "pid": os.getpid(),
            }
        )
