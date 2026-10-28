# Reflection 2: Module 2 (Data Contracts & Legacy Schemas)

## Take-away: what do I want to remember?
- A legacy database can look fine and still be full of mistakes. I have to prove each mistake with a query, not just describe it.
- A query can give a wrong answer without any error. The text price filter missed 9.90, and the join on a comma list silently dropped job 1.
- Many-to-many always needs a junction table. A list inside one column breaks 1NF.
- A natural key needs UNIQUE, otherwise it is not really a key (P-1003 was stored twice).
- The database (SQLAlchemy) and the app (Pydantic) protect the data in different places, and it is good to have both.

## What was good?
- Seeing real defects appear in the query results made the theory concrete.
- The data contract printed a clean, corrected schema with keys, real types and the job_part table.

## What was difficult, where did I struggle?
- Long pastes into Terminal broke or got cut off, and one double-pasted command overwrote my legacy.db. I fixed it by rebuilding everything from my setup script, which showed me why a setup script is important.
- Understanding the difference between an entity and an attribute, for example whether a technician is just a name or its own entity.

## Was there any good struggling or exploration?
- Working out why '9.90' < '15' is false when compared as text.
- Seeing that one duplicate part made job 2 appear twice in a join.

## Interaction with peers and instructors
We did the pod exchange (Task C) with the pod of Habiba Darwish ([her portfolio](https://github.com/Habiba-AladdinDarwish/Darwish_Databases_C2026)). We compared our study logs and sketches and discussed the three cardinalities:
- **1:1:** one machine has exactly one nameplate; the key goes on either side with UNIQUE.
- **1:n:** one machine has many sensors; the foreign key goes on the "many" side.
- **m:n:** work orders and parts need a junction table; a comma-separated list breaks 1NF.

We noted no open disagreement. The shared Discord image is still to be posted. Details are in my [study log, section 7](../Module02/study-log.md#7-agreed-learning-pod-discussion).

## Help and extra work
I used an AI assistant (Claude) to explain the concepts and guide me through the steps. I did not trust it blindly: every cardinality and defect is proven by a query result in audit-results.txt and task-b-proof-results.txt.

## Status
Tasks 1, 2 and 3 of the studio lab are done, plus the study log and the Task B sketches with a COUNT proof. Task C is done, except the shared Discord image.