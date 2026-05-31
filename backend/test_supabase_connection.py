#!/usr/bin/env python3
"""
Script para verificar la conexión a Supabase
Ejecutar: python test_supabase_connection.py
"""

import asyncio
import os
from dotenv import load_dotenv
import asyncpg

# Cargar variables de entorno
load_dotenv()

async def test_connection():
    """Test básico de conexión a Supabase"""
    
    # Obtener credenciales
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    db = os.getenv("POSTGRES_DB", "postgres")
    
    if not password or not host:
        print("ERROR: Credenciales incompletas en .env")
        print(f"  - POSTGRES_USER: {user}")
        print(f"  - POSTGRES_PASSWORD: {'***' if password else 'NO CONFIGURADA'}")
        print(f"  - POSTGRES_HOST: {host or 'NO CONFIGURADA'}")
        print(f"  - POSTGRES_PORT: {port}")
        print(f"  - POSTGRES_DB: {db}")
        return False
    
    print("[TEST] Intentando conectar a Supabase...")
    print(f"  Host: {host}:{port}")
    print(f"  Usuario: {user}")
    print(f"  Base de datos: {db}")
    
    try:
        # Crear pool de conexiones
        pool = await asyncpg.create_pool(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db,
            min_size=1,
            max_size=5,
            timeout=10
        )
        
        print("[OK] Pool de conexiones creado")
        
        # Obtener información del servidor
        async with pool.acquire() as conn:
            # Versión de PostgreSQL
            version = await conn.fetchval("SELECT version()")
            print(f"[OK] PostgreSQL: {version[:50]}...")
            
            # Listar tablas públicas
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            print(f"[OK] Tablas encontradas ({len(tables)}):")
            if tables:
                for table in tables:
                    table_name = table['table_name']
                    # Contar filas
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                    print(f"     - {table_name}: {count} filas")
            else:
                print("     (ninguna tabla pública)")
            
            # Probar query básica
            result = await conn.fetchval("SELECT 42 as answer")
            print(f"[OK] Query de prueba: {result}")
        
        await pool.close()
        
        print("\n[SUCCESS] Conexion a Supabase verificada exitosamente!")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] No se pudo conectar: {e}")
        print(f"Tipo de error: {type(e).__name__}")
        return False

async def main():
    print("=" * 60)
    print("PRUEBA DE CONEXIÓN SUPABASE - EnergyGrid")
    print("=" * 60 + "\n")
    
    success = await test_connection()
    
    print("\n" + "=" * 60)
    if success:
        print("Estatus: CONEXION EXITOSA")
    else:
        print("Estatus: CONEXION FALLIDA")
        print("\nVerifica:")
        print("  1. .env existe y tiene credenciales correctas")
        print("  2. Conexión a internet disponible")
        print("  3. Credenciales de Supabase son correctas")
        print("  4. Puerto 5432 no está bloqueado")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
