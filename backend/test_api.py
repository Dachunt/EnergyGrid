"""
Ejemplos de uso de la API EnergyGrid con Flask
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Credenciales admin por defecto
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin123!"

# ============================================================================
# 1. AUTENTICACIÓN
# ============================================================================

def test_login():
    """Prueba de login"""
    print("\n1. TEST LOGIN")
    print("-" * 60)
    
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD
        }
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(json.dumps(data, indent=2))
    
    return data.get('access_token')


def test_get_me(token):
    """Obtener información del usuario autenticado"""
    print("\n2. TEST GET ME")
    print("-" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/auth/me",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))


# ============================================================================
# 2. DISTRITOS
# ============================================================================

def test_get_districts():
    """Obtener todos los distritos"""
    print("\n3. TEST GET DISTRICTS")
    print("-" * 60)
    
    response = requests.get(f"{BASE_URL}/api/districts")
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Total distritos: {len(data)}")
    if data:
        print(json.dumps(data[0], indent=2))


def test_get_district(district_id):
    """Obtener un distrito específico"""
    print(f"\n4. TEST GET DISTRICT: {district_id}")
    print("-" * 60)
    
    response = requests.get(f"{BASE_URL}/api/districts/{district_id}")
    
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))


# ============================================================================
# 3. MÉTRICAS
# ============================================================================

def test_post_metric():
    """Enviar una métrica de consumo"""
    print("\n5. TEST POST METRIC")
    print("-" * 60)
    
    metric = {
        "substation_id": "SSS001",
        "distrito_id": "San Salvador",
        "consumo_kw": 3500.50,
        "capacidad_kw": 5000.00,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/metrics",
        json=metric
    )
    
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))


# ============================================================================
# 4. MONITOREO
# ============================================================================

def test_monitoring_health():
    """Obtener estado de salud del sistema"""
    print("\n6. TEST MONITORING HEALTH")
    print("-" * 60)
    
    response = requests.get(f"{BASE_URL}/api/monitoring/health")
    
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))


def test_monitoring_dashboard():
    """Obtener dashboard de monitoreo"""
    print("\n7. TEST MONITORING DASHBOARD")
    print("-" * 60)
    
    response = requests.get(f"{BASE_URL}/api/monitoring/dashboard")
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Métricas activas: {data.get('total_substations', 0)}")
    print(f"Alertas activas: {data.get('active_alerts_count', 0)}")
    print(json.dumps(data, indent=2))


def test_get_alerts():
    """Obtener alertas del sistema"""
    print("\n8. TEST GET ALERTS")
    print("-" * 60)
    
    response = requests.get(f"{BASE_URL}/api/monitoring/alerts")
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Total alertas: {len(data)}")
    if data:
        print(json.dumps(data[0], indent=2))


# ============================================================================
# 5. ADMIN
# ============================================================================

def test_list_users(token):
    """Listar todos los usuarios (admin)"""
    print("\n9. TEST LIST USERS (ADMIN)")
    print("-" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/admin/users",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Total usuarios: {len(data)}")
    if data:
        print(json.dumps(data[0], indent=2))


def test_list_substations(token):
    """Listar todas las subestaciones (admin)"""
    print("\n10. TEST LIST SUBSTATIONS (ADMIN)")
    print("-" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/api/admin/substations",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Total subestaciones: {len(data)}")
    if data:
        print(json.dumps(data[0], indent=2))


# ============================================================================
# 6. DEMO
# ============================================================================

def test_demo_metrics():
    """Obtener métricas de demo"""
    print("\n11. TEST DEMO METRICS")
    print("-" * 60)
    
    response = requests.get(f"{BASE_URL}/api/demo/metrics/sample")
    
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))


# ============================================================================
# 7. HEALTH CHECK
# ============================================================================

def test_health():
    """Health check del servidor"""
    print("\n12. TEST HEALTH CHECK")
    print("-" * 60)
    
    response = requests.get(f"{BASE_URL}/health")
    
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))


# ============================================================================
# MAIN
# ============================================================================

def run_all_tests():
    """Ejecutar todos los tests"""
    print("\n" + "=" * 60)
    print("PRUEBAS DE API - EnergyGrid Flask Backend")
    print("=" * 60)
    
    # Test de salud
    test_health()
    
    # Test de login
    token = test_login()
    if not token:
        print("ERROR: No se pudo obtener token")
        return
    
    # Test de autenticación
    test_get_me(token)
    
    # Tests de distritos
    test_get_districts()
    test_get_district("San Salvador")
    
    # Tests de métricas
    test_post_metric()
    
    # Tests de monitoreo
    test_monitoring_health()
    test_monitoring_dashboard()
    test_get_alerts()
    
    # Tests de admin
    test_list_users(token)
    test_list_substations(token)
    
    # Tests de demo
    test_demo_metrics()
    
    print("\n" + "=" * 60)
    print("PRUEBAS COMPLETADAS")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
