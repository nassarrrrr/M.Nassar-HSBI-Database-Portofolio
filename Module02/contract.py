"""Code-first data contract for the repaired maintenance schema."""
from datetime import date
from pydantic import BaseModel, Field, field_validator

from sqlalchemy import (Column, Date, ForeignKey, Integer, Numeric, String,
                        Table, MetaData, UniqueConstraint)

# --- 1. The contract the *application* validates against (Pydantic) ---
class Machine(BaseModel):
    machine_id: int = Field(ge=1)
    serial_no: str = Field(min_length=3)
    site: str
    installed: date                      # a real date, not free text

    @field_validator("serial_no")
    @classmethod
    def serial_has_prefix(cls, v: str) -> str:
        if not v.startswith("SN-"):
            raise ValueError("serial numbers must start with 'SN-'")
        return v

class MaintenanceJob(BaseModel):
    job_id: int
    machine_id: int                      # a foreign key, not a name
    technician: str
    done_on: date
    part_nos: list[str] = Field(default_factory=list)   # the m:n list, modeled properly

# --- 2. The contract the *database* enforces (SQLAlchemy DDL) ---
metadata = MetaData()

machine_t = Table("machine", metadata,
    Column("machine_id", Integer, primary_key=True),
    Column("serial_no", String, nullable=False),
    Column("site", String, nullable=False),
    Column("installed", Date, nullable=False),
    UniqueConstraint("serial_no", name="uq_machine_serial"),
)

part_t = Table("part", metadata,
    Column("part_no", String, primary_key=True),      # natural key, now enforced
    Column("description", String, nullable=False),
    Column("unit_price", Numeric(9, 2), nullable=False),   # NUMERIC, not TEXT
)

maint_job_t = Table("maint_job", metadata,
    Column("job_id", Integer, primary_key=True),
    Column("machine_id", Integer, ForeignKey("machine.machine_id"), nullable=False),
    Column("technician", String, nullable=False),
    Column("done_on", Date, nullable=False),
)

# the junction table that repairs the 1NF violation
job_part_t = Table("job_part", metadata,
    Column("job_id", Integer, ForeignKey("maint_job.job_id"), primary_key=True),
    Column("part_no", String, ForeignKey("part.part_no"), primary_key=True),
)

if __name__ == "__main__":
    # Emit the corrected DDL to prove the contract is buildable:
    from sqlalchemy.schema import CreateTable
    from sqlalchemy import create_engine
    engine = create_engine("sqlite://")
    metadata.create_all(engine)
    for t in (machine_t, part_t, maint_job_t, job_part_t):
        print(str(CreateTable(t).compile(engine)).strip(), ";\n")