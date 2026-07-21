from __future__ import annotations

import asyncio
from uuid import uuid4

from sqlalchemy import select

from supportmind.domain.common.enums import AgentRole, NodeType, Priority
from supportmind.infrastructure.auth.security import hash_password
from supportmind.infrastructure.db import models as m
from supportmind.infrastructure.db.session import SessionLocal, engine
from supportmind.infrastructure.db.models import Base


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        existing = await session.execute(select(m.AgentModel).limit(1))
        if existing.scalar_one_or_none():
            print("Database already seeded")
            return

        admin = m.AgentModel(
            id=uuid4(),
            email="admin@supportmind.ai",
            full_name="Ana Admin",
            hashed_password=hash_password("Admin123!"),
            roles=[AgentRole.ADMIN.value, AgentRole.SUPERVISOR.value],
            availability="available",
        )
        l1a = m.AgentModel(
            id=uuid4(),
            email="lucia@supportmind.ai",
            full_name="Lucía Pérez",
            hashed_password=hash_password("Agent123!"),
            roles=[AgentRole.AGENT_L1.value],
            availability="available",
        )
        l1b = m.AgentModel(
            id=uuid4(),
            email="marco@supportmind.ai",
            full_name="Marco Díaz",
            hashed_password=hash_password("Agent123!"),
            roles=[AgentRole.AGENT_L1.value],
            availability="available",
        )
        session.add_all([admin, l1a, l1b])

        products = [
            m.ProductModel(
                id=uuid4(), sku="IPH-15-128", name="iPhone 15 128GB", family="iphone", brand="Apple"
            ),
            m.ProductModel(
                id=uuid4(), sku="SGS-24-256", name="Samsung Galaxy S24", family="galaxy", brand="Samsung"
            ),
            m.ProductModel(
                id=uuid4(), sku="XIA-14T-256", name="Xiaomi 14T", family="xiaomi", brand="Xiaomi"
            ),
        ]
        session.add_all(products)

        for priority, response, resolution in [
            (Priority.P1, 15, 240),
            (Priority.P2, 30, 480),
            (Priority.P3, 60, 1440),
            (Priority.P4, 240, 2880),
        ]:
            session.add(
                m.SlaPolicyModel(
                    id=uuid4(),
                    priority=priority.value,
                    response_minutes=response,
                    resolution_minutes=resolution,
                )
            )

        # Decision tree: phone won't turn on
        tree_id = uuid4()
        n_root = uuid4()
        n_charged = uuid4()
        n_logo = uuid4()
        n_resolve_charge = uuid4()
        n_resolve_force = uuid4()
        n_escalate = uuid4()
        n_boot_loop = uuid4()

        tree = m.DecisionTreeModel(
            id=tree_id,
            slug="phone-power",
            name="Mi celular no enciende",
            version=1,
            is_active=True,
            root_node_id=n_root,
            description="Árbol de diagnóstico de encendido",
        )
        session.add(tree)

        nodes = [
            m.DecisionNodeModel(
                id=n_root,
                tree_id=tree_id,
                code="power_start",
                prompt="¿Cuál es el problema con tu celular?",
                node_type=NodeType.QUESTION.value,
            ),
            m.DecisionNodeModel(
                id=n_charged,
                tree_id=tree_id,
                code="charged_30min",
                prompt="¿Lo cargó durante al menos 30 minutos con el cargador original?",
                node_type=NodeType.QUESTION.value,
            ),
            m.DecisionNodeModel(
                id=n_logo,
                tree_id=tree_id,
                code="see_logo",
                prompt="¿Ve el logo del fabricante al intentar encenderlo?",
                node_type=NodeType.QUESTION.value,
            ),
            m.DecisionNodeModel(
                id=n_boot_loop,
                tree_id=tree_id,
                code="boot_loop",
                prompt="¿El logo aparece y desaparece en bucle?",
                node_type=NodeType.QUESTION.value,
            ),
            m.DecisionNodeModel(
                id=n_resolve_charge,
                tree_id=tree_id,
                code="resolve_charge",
                prompt=(
                    "Perfecto. Dejá el equipo cargando 30 minutos más y probá encenderlo con el "
                    "botón de encendido 10 segundos. Si vuelve a la normalidad, ¡listo!"
                ),
                node_type=NodeType.RESOLVE.value,
            ),
            m.DecisionNodeModel(
                id=n_resolve_force,
                tree_id=tree_id,
                code="resolve_force_restart",
                prompt=(
                    "Probá un reinicio forzado: volumen abajo + encendido 20 segundos. "
                    "Si el equipo inicia normalmente, el problema quedó resuelto."
                ),
                node_type=NodeType.RESOLVE.value,
            ),
            m.DecisionNodeModel(
                id=n_escalate,
                tree_id=tree_id,
                code="no_power",
                prompt=(
                    "No pude resolver el problema con las guías automáticas. "
                    "Voy a generar un ticket con un agente de Nivel 1."
                ),
                node_type=NodeType.ESCALATE.value,
            ),
        ]
        session.add_all(nodes)

        options = [
            m.DecisionOptionModel(id=uuid4(), node_id=n_root, label="Mi celular no enciende", next_node_id=n_charged, sort_order=1),
            m.DecisionOptionModel(id=uuid4(), node_id=n_root, label="Se reinicia solo / boot loop", next_node_id=n_boot_loop, sort_order=2),
            m.DecisionOptionModel(id=uuid4(), node_id=n_charged, label="Sí", next_node_id=n_logo, sort_order=1),
            m.DecisionOptionModel(id=uuid4(), node_id=n_charged, label="No", next_node_id=n_resolve_charge, sort_order=2),
            m.DecisionOptionModel(id=uuid4(), node_id=n_logo, label="Sí", next_node_id=n_boot_loop, sort_order=1),
            m.DecisionOptionModel(id=uuid4(), node_id=n_logo, label="No", next_node_id=n_escalate, sort_order=2),
            m.DecisionOptionModel(id=uuid4(), node_id=n_boot_loop, label="Sí", next_node_id=n_escalate, sort_order=1),
            m.DecisionOptionModel(id=uuid4(), node_id=n_boot_loop, label="No, se quedó en el logo", next_node_id=n_resolve_force, sort_order=2),
            m.DecisionOptionModel(id=uuid4(), node_id=n_boot_loop, label="El reinicio forzado no ayudó", next_node_id=n_escalate, sort_order=3),
        ]
        session.add_all(options)

        await session.commit()
        print("Seed completed")
        print("Agents:")
        print("  admin@supportmind.ai / Admin123!")
        print("  lucia@supportmind.ai / Agent123!")
        print("  marco@supportmind.ai / Agent123!")


if __name__ == "__main__":
    asyncio.run(seed())
