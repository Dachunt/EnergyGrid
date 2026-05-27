# 📊 EnergyGrid Dashboard - Complete Documentation

## Quick Navigation

### New to the Dashboard?
👉 Start here: **[DASHBOARD_QUICK_START.md](DASHBOARD_QUICK_START.md)** (5 minutes)

### Want Full Details?
👉 Read this: **[DASHBOARD_USAGE_GUIDE.md](DASHBOARD_USAGE_GUIDE.md)** (comprehensive guide)

### Need Integration Details?
👉 Check this: **[DASHBOARD_INTEGRATION_SUMMARY.md](DASHBOARD_INTEGRATION_SUMMARY.md)** (technical summary)

---

## 📋 All Documentation Files

| File | Purpose | Read Time |
|------|---------|-----------|
| **DASHBOARD_QUICK_START.md** | Get up and running in 5 minutes | 5 min |
| **DASHBOARD_USAGE_GUIDE.md** | Complete user manual with examples | 15 min |
| **DASHBOARD_INTEGRATION_SUMMARY.md** | Technical integration details | 10 min |
| **MONITORING_README.md** | Monitoring system overview | 20 min |
| **COMO_ESTA_INTEGRADO.md** | Architecture and design (Spanish) | 15 min |
| **MONITORING_GUIDE.md** | Developer integration guide | 20 min |

---

## 🎯 What is the Dashboard?

The **EnergyGrid Monitoring Dashboard** is a real-time visualization tool that displays:

- **System Metrics** (CPU, Memory, Disk, Network)
- **API Health** (Endpoint availability and response times)
- **Database Performance** (Slow query detection)
- **Alert Management** (Aggregated alerts with severity levels)

---

## ⚡ Quick Start (2 Steps)

```bash
# 1. Start the application
cd /d/ProyectoFinal/EnergyGrid/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. Open in browser
http://localhost:8000/dashboard
```

**That's it!** The dashboard will display real-time monitoring data.

---

## 📖 Documentation Sections

### For Users
- How to access the dashboard
- Interpreting metrics and alerts
- Understanding system health scores
- Troubleshooting common issues

### For Developers
- API endpoints documentation
- Integration examples
- Configuration options
- Architecture overview

### For Operators
- Deployment instructions
- Performance tuning
- Monitoring best practices
- Alert configuration

---

## 🚀 Features

✅ Real-time system monitoring
✅ Automatic health checks
✅ Slow query detection
✅ Color-coded alerting system
✅ Auto-refresh dashboard (configurable)
✅ 20+ API endpoints for data access
✅ No code modifications required
✅ Production-ready

---

## 📊 Dashboard Components

### 1. Health Score Card
Overall system health (0-100) combining:
- Resource utilization (Munin)
- Endpoint availability (Pingdom)
- Query performance (Slow Query Log)

### 2. Munin Metrics
Real-time system statistics:
- CPU usage percentage
- Memory (available vs used)
- Disk space utilization
- Network traffic (in/out)
- System load average
- Process count

### 3. Pingdom Health Checks
API endpoint monitoring:
- Health check status (UP/DOWN)
- Response time (milliseconds)
- Last check timestamp
- 24-hour uptime percentage

### 4. Slow Query Log
Database query performance:
- Query text and execution time
- Performance threshold violations
- Critical query detection
- Historical tracking

### 5. Alert Panel
Aggregated alerts from all monitors:
- Severity-based color coding
- Real-time alert stream
- Filtering and search
- Alert details on demand

---

## 🎛️ How to Use

### View Metrics
Dashboard loads automatically with data updating every 5 seconds

### Update Frequency
- Click refresh button for manual update
- Change update interval (5s, 10s, manual)
- Auto-refresh always enabled

### Filter Alerts
- Search by alert type
- Filter by severity
- View specific endpoint status

### Drill Down
- Click metric cards for details
- View query execution plans
- Check endpoint response times

---

## 🔧 Configuration

### Change Update Frequency
Edit `backend/app/static/dashboard.html`:
```javascript
const refreshInterval = 5000; // milliseconds (5 seconds)
```

### Modify Alert Thresholds
Edit `backend/app/services/monitoring_config.py`:
```python
THRESHOLDS = {
    'cpu_warning': 80,        # % CPU warning level
    'cpu_critical': 85,       # % CPU critical level
    'memory_warning': 80,     # % Memory warning level
    'memory_critical': 85,    # % Memory critical level
    'disk_warning': 80,       # % Disk warning level
    'disk_critical': 90,      # % Disk critical level
    'query_warning': 100,     # ms query warning level
    'query_critical': 500,    # ms query critical level
}
```

### Add More Endpoints to Monitor
Edit `backend/app/services/monitoring_config.py`:
```python
ENDPOINTS_TO_MONITOR = [
    '/health',
    '/api/metrics',
    '/api/districts',
    '/api/monitoring/health',
    '/your/custom/endpoint',  # Add here
]
```

---

## 🚨 When Something Goes Wrong

### Dashboard Not Loading
```bash
# Check if app is running
curl http://localhost:8000/health

# Check specific endpoint
curl http://localhost:8000/dashboard
```

### No Data Displaying
1. Wait 30 seconds (Munin needs time to collect initial data)
2. Check browser console for errors (F12)
3. Verify CORS is enabled (should be by default)

### Endpoint Shows DOWN
1. Test the endpoint manually: `curl http://localhost:8000/your-endpoint`
2. Check application logs for errors
3. Verify Pingdom configuration

For more troubleshooting, see **DASHBOARD_USAGE_GUIDE.md** section "🛠️ Solución de Problemas"

---

## 📈 API Access

You can also access monitoring data programmatically:

```bash
# Get system metrics
curl http://localhost:8000/api/monitoring/munin/metrics

# Get health status
curl http://localhost:8000/api/monitoring/health

# Get all alerts
curl http://localhost:8000/api/monitoring/alerts?severity=CRITICAL

# Get slow queries
curl http://localhost:8000/api/monitoring/queries/slow?limit=10
```

See **DASHBOARD_INTEGRATION_SUMMARY.md** for complete API reference.

---

## 📚 Learning Path

**Beginner** → **DASHBOARD_QUICK_START.md**
↓
**Intermediate** → **DASHBOARD_USAGE_GUIDE.md**
↓
**Advanced** → **DASHBOARD_INTEGRATION_SUMMARY.md**
↓
**Developer** → **MONITORING_GUIDE.md**

---

## ✨ What's Next?

After familiarizing yourself with the dashboard:

1. **Customize Thresholds** - Adjust alert levels for your system
2. **Add More Endpoints** - Monitor additional API routes
3. **Export Data** - Use API for custom reporting
4. **Integrate Alerts** - Add Slack/email notifications (future enhancement)
5. **Add Persistence** - Integrate InfluxDB/Prometheus (future enhancement)

---

## 📞 Need Help?

1. Read the relevant documentation file above
2. Check the troubleshooting section
3. Review the application logs: `tail -f backend/logs/app.log`
4. Verify your setup with the verification script
5. Check example integrations in `app/routes/monitoring_examples.py`

---

## ✅ Status

**Dashboard**: ✅ Complete and Production-Ready
**Version**: 1.0
**Last Updated**: May 25, 2024

---

**Ready to monitor?** → [DASHBOARD_QUICK_START.md](DASHBOARD_QUICK_START.md)
