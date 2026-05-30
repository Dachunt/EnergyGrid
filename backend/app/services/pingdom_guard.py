"""
Pingdom Guard - Guardia de disponibilidad
Verifica minuto a minuto que la plataforma responde y puede utilizarse
"""

import asyncio
import os
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, List
from urllib.parse import urlparse
import logging

logger = logging.getLogger("energygrid")

PINGDOM_API_BASE = "https://api.pingdom.com/api/3.1"


class PingdomGuard:
    """Monitor de disponibilidad y health check"""

    def __init__(self, check_interval: int = 60):
        """
        Initialize Pingdom Guard

        Args:
            check_interval: Intervalo de verificación en segundos (default: 60)
        """
        self.check_interval = check_interval
        self.uptime_history = []
        self.max_history = 1440  # 24 horas de datos por minuto
        self.endpoints = {}
        self.last_check = None
        self._pingdom_token = os.getenv("PINGDOM_API_TOKEN", "")
        self._pingdom_email = os.getenv("PINGDOM_EMAIL", "")
        self._pingdom_available = bool(self._pingdom_token and self._pingdom_email)
        self._pingdom_check_map: Dict[str, int] = {}  # local_name -> pingdom_check_id

    def _pingdom_headers(self, content_type: bool = False) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._pingdom_token}",
        }
        if content_type:
            headers["Content-Type"] = "application/json"
        return headers

    async def sync_with_pingdom(self) -> Dict[str, Any]:
        """Sincroniza checks locales con Pingdom API"""
        if not self._pingdom_available:
            return {"status": "skipped", "reason": "no_api_credentials"}

        result = {"created": 0, "updated": 0, "errors": 0, "remote_checks": []}

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # Get existing checks from Pingdom
                resp = await client.get(
                    f"{PINGDOM_API_BASE}/checks",
                    headers=self._pingdom_headers(),
                )
                if resp.status_code != 200:
                    logger.error(f"Pingdom API error: {resp.status_code} {resp.text}")
                    return {"status": "error", "detail": resp.text}

                data = resp.json()
                remote_checks = {c["name"]: c for c in data.get("checks", [])}
                result["remote_checks"] = list(remote_checks.keys())

                # Sync each local endpoint
                for name, cfg in self.endpoints.items():
                    pingdom_name = f"EnergyGrid-{name}"
                    parsed = urlparse(cfg["url"])
                    host = parsed.hostname or cfg["url"]
                    url_path = parsed.path or "/"
                    payload = {
                        "name": pingdom_name,
                        "host": host,
                        "url": url_path,
                        "resolution": 1,  # 1 minute
                        "type": "http",
                    }

                    if pingdom_name in remote_checks:
                        # Update existing check
                        cid = remote_checks[pingdom_name]["id"]
                        update_resp = await client.put(
                            f"{PINGDOM_API_BASE}/checks/{cid}",
                            headers=self._pingdom_headers(content_type=True),
                            json=payload,
                        )
                        if update_resp.status_code in (200, 201):
                            result["updated"] += 1
                        else:
                            result["errors"] += 1
                        self._pingdom_check_map[name] = cid
                    else:
                        # Create new check
                        create_resp = await client.post(
                            f"{PINGDOM_API_BASE}/checks",
                            headers=self._pingdom_headers(content_type=True),
                            json=payload,
                        )
                        if create_resp.status_code in (200, 201):
                            cid = create_resp.json().get("check", {}).get("id")
                            if cid:
                                self._pingdom_check_map[name] = cid
                                result["created"] += 1
                        else:
                            result["errors"] += 1

                result["status"] = "ok"

        except httpx.TimeoutException:
            logger.error("Pingdom API timeout")
            result["status"] = "error"
            result["detail"] = "timeout"
        except Exception as e:
            logger.error(f"Pingdom API error: {e}")
            result["status"] = "error"
            result["detail"] = str(e)

        logger.info("Pingdom sync completed", extra=result)
        return result

    async def fetch_pingdom_results(self) -> List[Dict[str, Any]]:
        """Obtiene resultados de checks desde Pingdom"""
        if not self._pingdom_available or not self._pingdom_check_map:
            return []

        results = []
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                for local_name, check_id in self._pingdom_check_map.items():
                    resp = await client.get(
                        f"{PINGDOM_API_BASE}/checks/{check_id}",
                        headers=self._pingdom_headers(),
                        params={"include_details": True},
                    )
                    if resp.status_code == 200:
                        data = resp.json().get("check", {})
                        results.append({
                            "local_name": local_name,
                            "pingdom_id": check_id,
                            "status": data.get("status", "unknown"),
                            "last_test_time": data.get("lasttesttime"),
                            "last_response_time": data.get("lastresponsetime"),
                            "resolution": data.get("resolution"),
                        })
        except Exception as e:
            logger.error(f"Error fetching Pingdom results: {e}")

        return results

    def add_endpoint(
        self, name: str, url: str, timeout: int = 5, expected_status: int = 200
    ):
        """Agrega un endpoint a monitorear"""
        self.endpoints[name] = {
            "url": url,
            "timeout": timeout,
            "expected_status": expected_status,
            "status": "unknown",
            "last_response_time": 0,
            "checks": [],
        }
        logger.info(f"Pingdom endpoint added: {name}")

    async def check_endpoint(self, name: str, endpoint_config: Dict) -> Dict[str, Any]:
        """Verifica un endpoint individual"""
        url = endpoint_config["url"]
        timeout = endpoint_config["timeout"]
        expected_status = endpoint_config["expected_status"]

        try:
            start_time = datetime.utcnow()
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                response_time = (datetime.utcnow() - start_time).total_seconds()

                is_up = response.status_code == expected_status
                status = "up" if is_up else "down"

                check_result = {
                    "timestamp": start_time.isoformat(),
                    "status": status,
                    "response_time_ms": round(response_time * 1000, 2),
                    "status_code": response.status_code,
                    "expected_status": expected_status,
                }

                # Guardar historial de checks
                endpoint_config["checks"].append(check_result)
                if len(endpoint_config["checks"]) > 100:
                    endpoint_config["checks"].pop(0)

                endpoint_config["status"] = status
                endpoint_config["last_response_time"] = response_time

                logger.info(
                    f"Pingdom check: {name}",
                    extra={
                        "endpoint": name,
                        "status": status,
                        "response_time_ms": check_result["response_time_ms"],
                    },
                )

                return check_result

        except asyncio.TimeoutError:
            logger.error(f"Pingdom timeout: {name}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "down",
                "error": "Timeout",
                "endpoint": name,
            }
        except Exception as e:
            logger.error(f"Pingdom check failed for {name}: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "down",
                "error": str(e),
                "endpoint": name,
            }

    async def run_checks(self) -> Dict[str, Any]:
        """Ejecuta verificaciones en todos los endpoints"""
        results = {}

        # Ejecutar checks en paralelo
        tasks = [
            self.check_endpoint(name, config) for name, config in self.endpoints.items()
        ]

        responses = await asyncio.gather(*tasks)

        for i, (name, _) in enumerate(self.endpoints.items()):
            results[name] = responses[i]

        self.last_check = datetime.utcnow().isoformat()

        # Agregar al historial
        uptime_record = {
            "timestamp": self.last_check,
            "endpoints": results,
            "overall_status": "up" if all(r.get("status") == "up" for r in results.values()) else "down",
        }
        self.uptime_history.append(uptime_record)

        if len(self.uptime_history) > self.max_history:
            self.uptime_history.pop(0)

        return uptime_record

    def get_endpoint_status(self, name: str) -> Dict[str, Any]:
        """Obtiene el estado de un endpoint específico"""
        if name not in self.endpoints:
            return {"error": "Endpoint not found"}

        endpoint = self.endpoints[name]
        recent_checks = endpoint["checks"][-10:] if endpoint["checks"] else []

        uptime_percentage = 0
        if recent_checks:
            up_count = sum(1 for check in recent_checks if check.get("status") == "up")
            uptime_percentage = round((up_count / len(recent_checks)) * 100, 2)

        return {
            "name": name,
            "url": endpoint["url"],
            "status": endpoint["status"],
            "last_response_time_ms": endpoint["last_response_time"] * 1000,
            "recent_checks": recent_checks,
            "uptime_percentage": uptime_percentage,
        }

    def get_all_status(self) -> Dict[str, Any]:
        """Obtiene el estado de todos los endpoints"""
        all_up = all(cfg["status"] == "up" for cfg in self.endpoints.values())

        endpoints_status = {}
        for name, config in self.endpoints.items():
            endpoints_status[name] = {
                "status": config["status"],
                "last_response_time_ms": round(config["last_response_time"] * 1000, 2),
            }

        return {
            "overall_status": "up" if all_up else "down",
            "endpoints": endpoints_status,
            "last_check": self.last_check,
            "total_endpoints": len(self.endpoints),
            "healthy_endpoints": sum(
                1 for cfg in self.endpoints.values() if cfg["status"] == "up"
            ),
        }

    def get_uptime_report(self, hours: int = 24) -> Dict[str, Any]:
        """Genera un reporte de disponibilidad"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        recent_history = [
            h for h in self.uptime_history
            if datetime.fromisoformat(h["timestamp"]) > cutoff_time
        ]

        if not recent_history:
            return {
                "period_hours": hours,
                "total_checks": 0,
                "uptime_percentage": 100,
            }

        total_checks = len(recent_history)
        successful_checks = sum(
            1 for h in recent_history if h.get("overall_status") == "up"
        )

        uptime_percentage = round((successful_checks / total_checks) * 100, 2)

        return {
            "period_hours": hours,
            "total_checks": total_checks,
            "successful_checks": successful_checks,
            "failed_checks": total_checks - successful_checks,
            "uptime_percentage": uptime_percentage,
        }

    def get_incidents(self) -> List[Dict[str, Any]]:
        """Obtiene lista de incidentes (cambios de estado)"""
        incidents = []
        previous_status = None

        for record in self.uptime_history[-100:]:  # Últimos 100 registros
            current_status = record.get("overall_status")

            if previous_status and previous_status != current_status:
                incidents.append({
                    "timestamp": record["timestamp"],
                    "from_status": previous_status,
                    "to_status": current_status,
                    "details": record.get("endpoints", {}),
                })

            previous_status = current_status

        return incidents
