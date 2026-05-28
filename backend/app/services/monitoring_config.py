"""
Monitoring Configuration
Archivo de configuración centralizado para el sistema de monitoreo
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from enum import Enum


class AlertSeverity(str, Enum):
    """Niveles de severidad de alertas"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MuninConfig:
    """Configuración de Munin Monitor"""
    
    # Historial
    max_history_records: int = 100
    
    # Umbrales de CPU
    cpu_warning_threshold: float = 80.0
    cpu_critical_threshold: float = 95.0
    
    # Umbrales de Memoria
    memory_warning_threshold: float = 85.0
    memory_critical_threshold: float = 95.0
    
    # Umbrales de Disco
    disk_warning_threshold: float = 80.0
    disk_critical_threshold: float = 90.0
    
    # Umbrales de Carga del Sistema
    system_load_warning_multiplier: float = 1.0  # CPU count * multiplier
    system_load_critical_multiplier: float = 1.5


@dataclass
class PingdomConfig:
    """Configuración de Pingdom Guard"""
    
    # Intervalo de verificación
    check_interval_seconds: int = 60
    
    # Timeout por defecto
    default_timeout_seconds: int = 5
    
    # Historial
    max_history_records: int = 1440  # 24 horas @ 1 check por minuto
    max_checks_per_endpoint: int = 100
    
    # Endpoints por defecto a monitorear
    default_endpoints: List[Dict[str, Any]] = field(default_factory=lambda: [
        {
            "name": "main_api",
            "url": "http://localhost:8000/health",
            "timeout": 5,
            "expected_status": 200,
        }
    ])
    
    # Uptime thresholds
    uptime_warning_threshold: float = 95.0  # % de disponibilidad
    uptime_critical_threshold: float = 80.0


@dataclass
class SlowQueryLogConfig:
    """Configuración de Slow Query Log"""
    
    # Umbral de query lenta
    slow_query_threshold_ms: float = 500.0
    
    # Umbrales adicionales
    warning_threshold_ms: float = 1000.0
    critical_threshold_ms: float = 2000.0
    
    # Historial
    max_history_records: int = 10000
    
    # Análisis de patrones
    max_pattern_records: int = 1000
    
    # Alertas
    high_slow_query_rate_threshold: float = 10.0  # %
    bottleneck_impact_threshold: float = 5.0
    
    # Limpieza automática
    auto_cleanup_enabled: bool = True
    cleanup_interval_hours: int = 24
    cleanup_older_than_hours: int = 168  # 1 semana


@dataclass
class MonitoringConfig:
    """Configuración centralizada del sistema de monitoreo"""
    
    # Componentes
    munin: MuninConfig = field(default_factory=MuninConfig)
    pingdom: PingdomConfig = field(default_factory=PingdomConfig)
    slow_query_log: SlowQueryLogConfig = field(default_factory=SlowQueryLogConfig)
    
    # Control general
    enabled: bool = True
    start_on_startup: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_metrics: bool = True
    log_queries: bool = True
    
    # Alertas
    alert_aggregation_enabled: bool = True
    alert_aggregation_window_seconds: int = 60
    
    # Persistencia (futuro)
    persist_metrics: bool = False
    persistence_backend: str = "memory"  # "memory", "influxdb", "prometheus"
    
    # Limpieza de recursos
    cleanup_on_shutdown: bool = True
    
    # Webhooks para alertas (futuro)
    webhook_enabled: bool = False
    webhook_urls: List[str] = field(default_factory=list)
    webhook_severity_filter: AlertSeverity = AlertSeverity.CRITICAL


# Instancia global de configuración
_monitoring_config: MonitoringConfig = MonitoringConfig()


def get_monitoring_config() -> MonitoringConfig:
    """Obtiene la configuración global del monitoreo"""
    return _monitoring_config


def set_monitoring_config(config: MonitoringConfig):
    """Establece la configuración global del monitoreo"""
    global _monitoring_config
    _monitoring_config = config


def get_default_config() -> MonitoringConfig:
    """Obtiene configuración por defecto"""
    return MonitoringConfig()


def load_config_from_dict(config_dict: Dict[str, Any]) -> MonitoringConfig:
    """Carga configuración desde diccionario"""
    config = get_default_config()
    
    if "munin" in config_dict:
        munin_cfg = config_dict["munin"]
        config.munin = MuninConfig(**munin_cfg)
    
    if "pingdom" in config_dict:
        pingdom_cfg = config_dict["pingdom"]
        config.pingdom = PingdomConfig(**pingdom_cfg)
    
    if "slow_query_log" in config_dict:
        sql_cfg = config_dict["slow_query_log"]
        config.slow_query_log = SlowQueryLogConfig(**sql_cfg)
    
    return config


# Presets de configuración


class MonitoringPresets:
    """Presets de configuración predefinidos"""
    
    @staticmethod
    def development() -> MonitoringConfig:
        """Configuración para desarrollo"""
        config = get_default_config()
        config.munin.max_history_records = 50
        config.pingdom.max_history_records = 100
        config.slow_query_log.max_history_records = 1000
        config.log_level = "DEBUG"
        return config
    
    @staticmethod
    def production() -> MonitoringConfig:
        """Configuración para producción"""
        config = get_default_config()
        config.munin.max_history_records = 1000
        config.pingdom.max_history_records = 4320  # 72 horas
        config.slow_query_log.max_history_records = 50000
        config.slow_query_log.auto_cleanup_enabled = True
        config.alert_aggregation_enabled = True
        config.log_level = "WARNING"
        config.webhook_enabled = True
        return config
    
    @staticmethod
    def minimal() -> MonitoringConfig:
        """Configuración mínima (recursos limitados)"""
        config = get_default_config()
        config.munin.max_history_records = 10
        config.pingdom.max_history_records = 24
        config.slow_query_log.max_history_records = 100
        config.slow_query_log.auto_cleanup_enabled = True
        config.cleanup_interval_hours = 1
        return config
    
    @staticmethod
    def aggressive() -> MonitoringConfig:
        """Configuración agresiva (máximas métricas)"""
        config = get_default_config()
        config.munin.max_history_records = 5000
        config.pingdom.max_history_records = 10000
        config.slow_query_log.max_history_records = 100000
        config.slow_query_log.slow_query_threshold_ms = 100.0  # Más sensible
        return config


# Cargar desde variables de entorno (opcional)
def load_from_env():
    """Carga configuración desde variables de entorno"""
    import os
    
    config = get_default_config()
    
    # Munin
    if os.getenv("MONITORING_MUNIN_ENABLED", "true").lower() == "false":
        config.enabled = False
    
    cpu_threshold = os.getenv("MONITORING_CPU_THRESHOLD")
    if cpu_threshold:
        config.munin.cpu_warning_threshold = float(cpu_threshold)
    
    # Pingdom
    check_interval = os.getenv("MONITORING_CHECK_INTERVAL_SECONDS")
    if check_interval:
        config.pingdom.check_interval_seconds = int(check_interval)
    
    # Slow Query Log
    slow_threshold = os.getenv("MONITORING_SLOW_QUERY_THRESHOLD_MS")
    if slow_threshold:
        config.slow_query_log.slow_query_threshold_ms = float(slow_threshold)
    
    set_monitoring_config(config)
    return config


if __name__ == "__main__":
    # Ejemplos de uso
    print("=== Configuración por defecto ===")
    default_cfg = get_default_config()
    print(f"CPU Warning: {default_cfg.munin.cpu_warning_threshold}%")
    print(f"Slow Query Threshold: {default_cfg.slow_query_log.slow_query_threshold_ms}ms")
    
    print("\n=== Configuración Development ===")
    dev_cfg = MonitoringPresets.development()
    print(f"Max Munin Records: {dev_cfg.munin.max_history_records}")
    
    print("\n=== Configuración Production ===")
    prod_cfg = MonitoringPresets.production()
    print(f"Max Munin Records: {prod_cfg.munin.max_history_records}")
