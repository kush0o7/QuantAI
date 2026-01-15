import importlib
import os
from pathlib import Path


def test_ingest_from_fixtures():
    fixtures_path = Path(__file__).parents[2] / "data" / "fixtures"
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    os.environ["FIXTURES_PATH"] = str(fixtures_path)

    from core.config import get_settings

    get_settings.cache_clear()

    import data.storage.db as db
    
    importlib.reload(db)
    db.init_db()

    with db.SessionLocal() as session:
        tenant = db.Tenant(name="Test Tenant")
        session.add(tenant)
        session.commit()
        session.refresh(tenant)

        company = db.Company(tenant_id=tenant.id, name="Acme AI", domain="acme-ai.com")
        session.add(company)
        session.commit()
        session.refresh(company)

        from agents.signal_harvester.agent import SignalHarvesterAgent

        harvester = SignalHarvesterAgent(session)
        inserted = harvester.harvest(company, source="mock")

        assert inserted > 0
        assert session.query(db.SignalEvent).count() == inserted
