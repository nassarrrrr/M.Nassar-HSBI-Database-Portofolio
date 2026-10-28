# Reflection 1 in Module 1

- # Reflection 1: Module 1

## Take-away: what do I want to remember?
- A database can be a single file inside my program (SQLite). A server is only
  worth it when there is a measured need for one.
- A query can run and still be wrong. SQL Island rejected queries that returned
  the wrong columns or rows, and an AI-written query needs checking too. I have
  to verify the result, not just the syntax.
- Before an UPDATE or DELETE, check the WHERE part. Without it, every row changes.
- Read the error message. "no such column: YOUR_PERSONID" told me exactly what
  was wrong.

My advice to a new student: do the Git and uv setup early and slowly, and ask
a teammate when you are stuck. Most of my time went into setup problems, not SQL.

## What was good?
- The uv setup: one tool installed Python and every library, and `uv-check.py`
  proved it worked.
- SQL Island made SQL concrete. Seeing "Yeah!" after a correct query was
  motivating.
- Working in the sqlite3 shell and saving the session as evidence.
- Loading generated machine telemetry into SQLite with a script and querying it
  from Python, which showed that a whole database is just one file.
- Checking an AI-written query with EXPLAIN QUERY PLAN instead of trusting it.

## What was difficult, where did I struggle?
- Git and GitHub were the hardest part, because I had never used them before.
  The Terminal push failed because GitHub does not accept passwords, my first
  tokens did not have the right permission, and GitHub Desktop first opened a
  different copy of my repo than the one I had worked in.
- Knowing which folder the Terminal was in. Several times Git said "not a git
  repository" because I was in my home folder.
- Small mistakes broke commands: a typo (`sqlalchemyv`) and a placeholder
  (`YOUR_PERSONID`) that I submitted without replacing.

## Was there any good struggling or exploration?
- SQL Island's message "The columns are wrong". I had to work out that the game
  compares which columns I return, not only the rows.
- Joins across tables, and mixing AND with OR using brackets.
- Show stopper: the Git authentication problem blocked me for a long time.

## Interaction with peers and instructors
I worked with my pod and teammates during the session. We compared results,
helped each other with setup problems, and my teammates are linked in my
Module 1 README.

## Help and extra work
Who helped me? I used an AI assistant (Claude) to guide me step by step through
the setup, Git and SQL Island. It was valuable, but I did not trust it blindly:
I ran `git status`, `git log` and `uv-check.py` and read the output. Two of its
suggestions did not work as written (a query that used `SELECT *` and a
placeholder I had to replace), and I fixed them from the error messages.

Who did I help? I helped my teammates with their setup and exercises.

Did I present, implement, make a PR, or fix something crucial for the class?
Not yet.

## Status
I completed all seven tasks of Module 1. My evidence is in this folder and in
the repository: the uv check output, the shell tour, the SQL Island answers
and screenshot, and the telemetry and query results.