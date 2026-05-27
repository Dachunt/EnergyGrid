#!/bin/bash
# QUICK START - Sistema de Monitoreo EnergyGrid

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  🚀 QUICK START - Sistema de Monitoreo EnergyGrid             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}📋 Pasos para comenzar:${NC}\n"

echo "1️⃣  Instalar dependencias"
echo -e "   ${YELLOW}$ cd backend${NC}"
echo -e "   ${YELLOW}$ pip install -r requirements.txt${NC}"
echo ""

echo "2️⃣  Iniciar el servidor"
echo -e "   ${YELLOW}$ python -m uvicorn app.main:app --reload${NC}"
echo ""

echo "3️⃣  Ver documentación"
echo -e "   ${GREEN}✅ MONITORING_README.md${NC} - Guía para usuarios"
echo -e "   ${GREEN}✅ MONITORING_GUIDE.md${NC} - Guía técnica"
echo -e "   ${GREEN}✅ INTEGRATION_SUMMARY.txt${NC} - Resumen visual"
echo ""

echo "4️⃣  Probar los endpoints (en otra terminal)"
echo ""
echo "   Dashboard completo:"
echo -e "   ${YELLOW}curl http://localhost:8000/api/monitoring/dashboard${NC}"
echo ""
echo "   Health del sistema:"
echo -e "   ${YELLOW}curl http://localhost:8000/api/monitoring/health${NC}"
echo ""
echo "   Alertas críticas:"
echo -e "   ${YELLOW}curl 'http://localhost:8000/api/monitoring/alerts?severity=critical'${NC}"
echo ""
echo "   Queries lentas:"
echo -e "   ${YELLOW}curl http://localhost:8000/api/monitoring/queries/slow${NC}"
echo ""

echo "5️⃣  Ejecutar tests de validación"
echo -e "   ${YELLOW}$ python test_monitoring.py${NC}"
echo ""

echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}✅ 8 Herramientas/Componentes Integrados:${NC}"
echo "   🔵 Munin Monitor"
echo "   🟠 Pingdom Guard"
echo "   🟢 Slow Query Log"
echo "   ⚙️  Orchestrator Central"
echo "   📊 Dashboard Consolidado"
echo "   🔔 Alertas Automáticas"
echo "   🛣️  20+ Endpoints API"
echo "   📚 Documentación Completa"
echo ""

echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Más información:${NC}"
echo "   - Lee MONITORING_README.md para guía completa"
echo "   - Consulta MONITORING_GUIDE.md para detalles técnicos"
echo "   - Ver monitoring_examples.py para código de ejemplo"
echo ""
echo -e "${GREEN}✅ Sistema listo para usar${NC}"
echo ""
