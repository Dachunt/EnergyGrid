async def redistribuir_carga(pool, district_id: str):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (district_id)
                district_id,
                porcentaje_uso::float8 AS porcentaje_uso
            FROM consumo_temporal
            ORDER BY district_id, timestamp DESC
            """
        )

    candidatos = []
    for row in rows:
        if row["district_id"] == district_id:
            continue
        if row["porcentaje_uso"] < 75:
            candidatos.append(
                {
                    "district_id": row["district_id"],
                    "porcentaje_uso": round(row["porcentaje_uso"], 2),
                }
            )

    candidatos.sort(key=lambda x: x["porcentaje_uso"])
    return candidatos[:3]
