# Module 2: Data Contracts & Reading Legacy Schemas

## Learning goals
1. Reconstruct an ER/EER model (entities, attributes, keys, relationships, cardinalities) from an undocumented SQL schema.
2. Identify integrity defects (missing foreign keys, orphan rows, redundant data, normalization violations) with queries, not intuition.
3. Distinguish an entity, a relationship and an attribute, and a surrogate key from a natural key, and justify the choice.
4. Express a schema as a code-first data contract (Pydantic / SQLAlchemy) that an application can enforce.
5. Write the requirements the schema forgot: the business rules nobody encoded.

## Studio lab: auditing the legacy maintenance schema
- Setup (rebuilds legacy.db): [setup_legacy.sh](setup_legacy.sh)
- ER model, cardinalities and the 5 defects with production impact: [er-audit.md](er-audit.md)
- Audit queries: [audit.sql](audit.sql), results: [audit-results.txt](audit-results.txt)
- Data contract: [contract.py](contract.py), emitted corrected DDL: [contract-ddl.sql](contract-ddl.sql)

## Task 3: what is enforced in the model vs. in the database
- **In the database (SQLAlchemy DDL):** primary keys, the UNIQUE serial number, NOT NULL, NUMERIC prices, DATE columns, and foreign keys including the job_part junction table. These rules protect the data no matter which program writes to it.
- **In the model (Pydantic):** the rule that a serial number must start with "SN-", and that a date must be a real date before it is saved. These are business rules, and the app can give a clear error message to the user before anything reaches the database.
- **Why both:** the database is the last safety net, and the model catches mistakes early with readable errors.
- **Note:** SQLite does not check foreign keys unless `PRAGMA foreign_keys = ON` is set for each connection.

## Requirements the schema forgot (business rules)
- Every maintenance job must belong to a machine that exists.
- A part number is unique, and a job can list a given part only once.
- Prices are money (numbers with 2 decimals), never text.
- Every machine has a real install date.
- A technician should be a person in a technician table, not a free-text name, so "Beier" and "beier" cannot become two people.

## Reflection
[Reflection 2](../Reflections/ref02.md)