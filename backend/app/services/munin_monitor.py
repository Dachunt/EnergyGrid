"""
Munin Monitor - Sensor universal de métricas del sistema
Monitorea: procesos activos, memoria, red, disco y carga del servidor
"""

import psutil
import time
from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger("energygrid")


class MuninMonitor:
    """Monitor de métricas del sistema en tiempo real"""

    def __init__(self):
        self.metrics_history = []
        self.max_history = 100

    def get_cpu_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de CPU"""
        return {
            "percent": psutil.cpu_percent(interval=0.1),
            "count": psutil.cpu_count(),
            "per_cpu": psutil.cpu_percent(interval=0.1, percpu=True),
            "load_average": psutil.getloadavg() if hasattr(psutil, "getloadavg") else None,
        }

    def get_memory_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de memoria"""
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent,
            "available_percent": 100 - mem.percent,
        }

    def get_network_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de red"""
        net = psutil.net_io_counters()
        return {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
            "errors_in": net.errin,
            "errors_out": net.errout,
            "dropped_in": net.dropin,
            "dropped_out": net.dropout,
        }

    def get_disk_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de disco"""
        disk = psutil.disk_usage("/")
        return {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": disk.percent,
        }

    def get_processes_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de procesos"""
        try:
            processes = psutil.pids()
            memory_processes = []

            for pid in processes[:10]:  # Top 10 procesos por memoria
                try:
                    p = psutil.Process(pid)
                    memory_processes.append(
                        {
                            "pid": pid,
                            "name": p.name(),
                            "memory_mb": round(p.memory_info().rss / (1024**2), 2),
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            memory_processes.sort(key=lambda x: x["memory_mb"], reverse=True)
            return {
                "total_processes": len(processes),
                "top_memory_processes": memory_processes[:5],
            }
        except Exception as e:
            logger.error(f"Error getting process metrics: {e}")
            return {"total_processes": 0, "top_memory_processes": []}

    def get_system_load(self) -> Dict[str, Any]:
        """Obtiene la carga general del sistema"""
        try:
            load = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0, 0, 0)
            cpu_count = psutil.cpu_count()
            return {
                "load_1m": round(load[0], 2),
                "load_5m": round(load[1], 2),
                "load_15m": round(load[2], 2),
                "cpu_count": cpu_count,
                "load_percentage": round((load[0] / cpu_count * 100), 2) if cpu_count else 0,
            }
        except Exception as e:
            logger.error(f"Error getting system load: {e}")
            return {"load_1m": 0, "load_5m": 0, "load_15m": 0, "cpu_count": 0, "load_percentage": 0}

    def collect_metrics(self) -> Dict[str, Any]:
        """Recopila todas las métricas del sistema"""
        timestamp = datetime.utcnow().isoformat()
        metrics = {
            "timestamp": timestamp,
            "cpu": self.get_cpu_metrics(),
            "memory": self.get_memory_metrics(),
            "disk": self.get_disk_metrics(),
            "network": self.get_network_metrics(),
            "processes": self.get_processes_metrics(),
            "system_load": self.get_system_load(),
        }

        # Agregar al historial
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history:
            self.metrics_history.pop(0)

        logger.info("Munin metrics collected", extra={"metrics_timestamp": timestamp})
        return metrics

    def get_alerts(self) -> list:
        """Genera alertas basadas en umbral de métricas"""
        alerts = []
        latest_metrics = self.metrics_history[-1] if self.metrics_history else None

        if not latest_metrics:
            return alerts

        # Alert: CPU alto
        if latest_metrics["cpu"]["percent"] > 80:
            alerts.append({
                "type": "cpu_high",
                "severity": "warning",
                "value": latest_metrics["cpu"]["percent"],
                "message": f"CPU utilización alta: {latest_metrics['cpu']['percent']}%",
            })

        # Alert: Memoria alta
        if latest_metrics["memory"]["percent"] > 85:
            alerts.append({
                "type": "memory_high",
                "severity": "critical",
                "value": latest_metrics["memory"]["percent"],
                "message": f"Memoria utilización crítica: {latest_metrics['memory']['percent']}%",
            })

        # Alert: Disco lleno
        if latest_metrics["disk"]["percent"] > 90:
            alerts.append({
                "type": "disk_full",
                "severity": "critical",
                "value": latest_metrics["disk"]["percent"],
                "message": f"Disco casi lleno: {latest_metrics['disk']['percent']}%",
            })

        # Alert: Carga del sistema
        if latest_metrics["system_load"]["load_percentage"] > 100:
            alerts.append({
                "type": "system_overloaded",
                "severity": "warning",
                "value": latest_metrics["system_load"]["load_percentage"],
                "message": f"Sistema sobrecargado: {latest_metrics['system_load']['load_percentage']}%",
            })

        return alerts

    def get_health_score(self) -> float:
        """Calcula un score de salud del sistema (0-100)"""
        if not self.metrics_history:
            return 100.0

        latest = self.metrics_history[-1]
        score = 100.0

        # Restar puntos por métricas altas
        score -= min(latest["cpu"]["percent"] / 2, 20)  # Máx 20 puntos
        score -= min(latest["memory"]["percent"] / 2, 20)  # Máx 20 puntos
        score -= min(latest["disk"]["percent"] / 3, 15)  # Máx 15 puntos
        score -= min(latest["system_load"]["load_percentage"] / 2, 20)  # Máx 20 puntos

        return max(score, 0)
