from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.db.models import ModelRunLog
from app.schemas.governance import ModelGovernance

logger = logging.getLogger(__name__)


def log_model_run(db: Session, governance: ModelGovernance, module: str, inputs: dict, outputs_summary: dict) -> ModelRunLog | None:
    """Best-effort audit write. A missing/unreachable database must never break a forecast or
    economics response — it degrades to "no audit row", logged loudly, not a 500.
    """
    row = ModelRunLog(
        model_name=governance.model_name,
        model_version=governance.model_version,
        module=module,
        random_seed=governance.random_seed,
        data_quality=governance.data_quality.value,
        inputs_json=inputs,
        outputs_summary_json=outputs_summary,
    )
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception:
        logger.warning("Audit log write failed (DB unavailable?) — continuing without it.", exc_info=True)
        db.rollback()
        return None
