# 🚀 QUICK START: Sistema de Monitoreo EnergyGrid

**Tiempo estimado**: 5 minutos

---

## 1️⃣ Instalar Dependencias

```bash
cd backend
pip install -r requirements.txt
```

Si hay problemas, instala solo lo necesario:
```bash
pip install psutil httpx fastapi uvicorn
```

---

## 2️⃣ Iniciar la Aplicación

```bash
cd backend
python -m uvicorn app.main:app --reload
```

Deberías ver:
```
Initializing monitoring system...
Monitoring system initialized and running
```

---

## 3️⃣ Probar los Endpoints

### Dashboard Completo
```bash
curl http://localhost:8000/api/monitoring/dashboard
```

### Health General
```bash
curl http://localhost:8000/api/monitoring/health
```

### Apenas Alertas
```bash
curl http://localhost:8000/api/monitoring/alerts
```

### Queries Lentas
```bash
curl http://localhost:8000/api/monitoring/queries/slow
```

---

## 4️⃣ Validar Instalación

```bash
python validate_monitoring.py
```

---

## 📊 Las 3 Herramientas

### 🔵 Munin (Sensor Universal)
- Mide: CPU, memoria, disco, red, procesos
- Endpoint: `/api/monitoring/munin/metrics`
- Health Score: `/api/monitoring/munin/health`

### 🟠 Pingdom (Guardia)
- Verifica endpoints cada minuto
- Estado: `/api/monitoring/pingdom/status`
- Uptime: `/api/monitoring/pingdom/uptime?hours=24`

### 🟢 Slow Query Log (Tráfico BD)
- Identifica queries lentas
- Listas: `/api/monitoring/queries/slow`
- Cuellos: `/api/monitoring/queries/bottlenecks`

---

## 🎯 Próximos Pasos

1. Revisa `INTEGRATION_GUIDE_COMPLETE.md` para uso avanzado
2. Revisa `MONITORING_README.md` para ejemplos
3. Configura alertas personalizadas (opcional)
4. Integra con tu frontend (opcional)

---

**Estado**: ✅ Listo para usar
