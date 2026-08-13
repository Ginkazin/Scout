import asyncio

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.plan import Plan

DEFAULT_PLANS = [
    {
        "name": "FREE",
        "price": 0,
        "max_customers": 1,
        "max_servers": 3,
        "max_users": 1,
        "retention_days": 5,
    },
    {
        "name": "STARTER",
        "price": 49.90,
        "max_customers": 5,
        "max_servers": 15,
        "max_users": 5,
        "retention_days": 5,
    },
    {
        "name": "PRO",
        "price": 129.90,
        "max_customers": 20,
        "max_servers": 100,
        "max_users": 10,
        "retention_days": 5,
    },
]


async def seed_plans() -> None:
    async with SessionLocal() as db:
        for plan_data in DEFAULT_PLANS:
            result = await db.execute(
                select(Plan).where(Plan.name == plan_data["name"])
            )
            existing = result.scalar_one_or_none()

            if existing is not None:
                print(f"Plano '{plan_data['name']}' já existe, pulando.")
                continue

            plan = Plan(**plan_data)
            db.add(plan)
            print(f"Plano '{plan_data['name']}' criado.")

        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed_plans())