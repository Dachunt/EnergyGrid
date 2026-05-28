# 🚀 Dashboard - Quick Start

## En 5 Minutos

### 1️⃣ Iniciar la Aplicación

```bash
cd /d/ProyectoFinal/EnergyGrid/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Deberías ver algo como:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     EnergyGrid startup complete - Monitoring system initialized
```

### 2️⃣ Abrir el Dashboard

Abre tu navegador y ve a:
```
http://localhost:8000/dashboard
```

### 3️⃣ Ver los Datos

¡El dashboard debería mostrar:
- 🔵 **Munin**: Métricas del sistema (CPU, memoria, disco)
- 🟠 **Pingdom**: Estado de endpoints
- 🟢 **Slow Query Log**: Queries lentas

---

## 🎯 Lo Básico

### ¿Qué Veo?

| Sección | ¿Qué Significa? |
|---------|-----------------|
| **Health Score** | Salud general del sistema (0-100) |
| **CPU, Memory, Disk** | Uso de recursos del servidor |
| **Endpoints** | Si tus APIs están disponibles |
| **Alerts** | Problemas detectados |
| **Slow Queries** | Queries que tardaron demasiado |

### ¿Qué Significa Cada Color?

- 🟢 **Verde**: Todo bien
- 🟡 **Amarillo**: Cuidado, casi en límite
- 🔴 **Rojo**: Problema, requiere atención

---

## 📊 Ejemplo de Uso Real

### Escenario 1: CPU Alta

```
Ves: CPU Usage 92% en rojo

Acciones:
1. Haz click en CPU para ver detalles
2. Identifica qué proceso usa más CPU
3. Optimiza o reinicia ese proceso
```

### Escenario 2: Endpoint Down

```
Ves: Endpoint "/api/metrics" DOWN

Acciones:
1. Verifica si la app sigue corriendo
2. Revisa los logs: tail -f backend/logs/app.log
3. Reinicia si es necesario
```

### Escenario 3: Query Lenta

```
Ves: Query tardó 1200ms en rojo

Acciones:
1. Lee la query en "Slow Query Log"
2. Optimiza con índices o reescribe
3. Verifica tiempo de ejecución nuevamente
```

---

## 🎛️ Controles

- **Refresh**: Botón en la esquina superior derecha
- **Selector de Actualización**: 5s, 10s, Manual
- **Filtros**: Busca tipos de alerta específicos
- **Auto-refresh**: El dashboard se actualiza automáticamente

---

## ⚠️ Problemas Comunes

### "Página no encontrada"
- Verifica que pusiste `http://` (no `https://`)
- Verifica que el puerto sea `8000`
- Recarga la página

### "Conectando... por favor espera"
- Espera a que la app termine de iniciar (ver logs)
- Verifica que no haya errores de base de datos
- Refresca manualmente

### "No hay datos"
- Espera a que Munin recopile datos (30 segundos)
- Verifica que la app esté corriendo: `curl http://localhost:8000/health`

---

## 📖 Siguiente Paso

Leer la guía completa: **DASHBOARD_USAGE_GUIDE.md**

