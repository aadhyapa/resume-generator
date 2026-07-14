High-Level Architecture
User Resume
    ↓
Parse Resume
    ↓
Store Bullets Individually
    ↓
Generate Embeddings
    ↓
Save to Database

Job Description
    ↓
Generate Embedding
    ↓
Compare Against Resume Bullets
    ↓
Rank Bullets
    ↓
Select Best Bullets
    ↓
LLM Rewrites Selected Bullets
    ↓
Generate Final Resume
Step 1: Define Your Data Model

Don't store a resume as one giant text blob.

Store every bullet independently.

Example table:

CREATE TABLE resume_items (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    section TEXT,
    company TEXT,
    title TEXT,
    text TEXT,
    start_date DATE,
    embedding JSONB
);

Example row:

{
  "section": "experience",
  "company": "Acme",
  "title": "Software Engineer",
  "text": "Built ML models for fraud detection."
}
Step 2: Choose an Embedding Model

For an MVP, use:

OpenAI's embedding API
model: text-embedding-3-small

Why?

Cheap
Fast
Good semantic quality
Step 3: Generate an Embedding

Install:

pip install openai

Python:

from openai import OpenAI

client = OpenAI()

response = client.embeddings.create(
    model="text-embedding-3-small",
    input="Built ML models for fraud detection."
)

embedding = response.data[0].embedding

Now:

print(len(embedding))

Returns something like:

1536

That means you now have a 1536-dimensional vector representing the meaning of that bullet.

Step 4: Store the Embedding

For an MVP:

resume_item["embedding"] = embedding

Store it in:

PostgreSQL JSONB
SQLite JSON
MongoDB

Example:

{
  "text": "Built ML models for fraud detection.",
  "embedding": [0.123, -0.442, ...]
}

You only need to generate this once per bullet.

Step 5: Embed Every Resume Item

When the user uploads their resume:

for bullet in resume_bullets:
    embedding = create_embedding(bullet)
    save_to_db(bullet, embedding)

Do the same for:

Experience bullets
Projects
Coursework
Leadership
Research

Everything becomes searchable.

Step 6: Embed the Job Description

Suppose the user pastes:

Looking for a Machine Learning Engineer with
Python, AWS, and SQL experience.

Generate:

job_embedding = create_embedding(job_description)
Step 7: Compute Similarity

Install:

pip install numpy

Function:

import numpy as np

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)

    return np.dot(a, b) / (
        np.linalg.norm(a) *
        np.linalg.norm(b)
    )

Usage:

score = cosine_similarity(
    bullet_embedding,
    job_embedding
)

Example results:

ML bullet        0.92
AWS bullet       0.87
React bullet     0.53
Marketing bullet 0.12
Step 8: Rank Everything
items = []

for bullet in resume_items:

    score = cosine_similarity(
        bullet.embedding,
        job_embedding
    )

    items.append({
        "text": bullet.text,
        "score": score
    })

Sort:

items.sort(
    key=lambda x: x["score"],
    reverse=True
)

Now your most relevant bullets are at the top.

Step 9: Add Skill Matching

Embeddings are good.

Skill matching makes them better.

Use an LLM once:

Prompt:

Extract all technical skills from this job description.

Return JSON only.

Output:

{
  "skills": [
    "python",
    "aws",
    "sql",
    "machine learning"
  ]
}

Store:

required_skills
Skill Overlap Function

Bullet:

Built ML models using Python.

Metadata:

[
  "python",
  "machine learning"
]

Score:

matches = 2
required = 4

skill_overlap = matches / required

Result:

0.50
Step 10: Add Recency

Current job:

1.0

Last job:

0.8

Older:

0.6

Simple is sufficient.

Example:

from datetime import datetime

years_old = current_year - end_year

recency = 1 / (1 + years_old)
Step 11: Final Score
final_score = (
    0.6 * semantic_similarity +
    0.3 * skill_overlap +
    0.1 * recency
)

Store:

item["final_score"]

Then sort.

Step 12: Select Content

Example constraints:

MAX_EXPERIENCE_BULLETS = 12
MAX_PROJECTS = 3
MAX_COURSES = 4

Select highest-scoring items until limits are reached.

Step 13: Rewrite with an LLM

Only after you've chosen the bullets.

Prompt:

Rewrite these bullets.

Rules:
- Max 2 lines
- Preserve facts
- Emphasize:
  Python
  AWS
  Machine Learning

Input:

Built predictive models for fraud detection.

Output:

Developed Python-based machine learning models for fraud detection, improving prediction accuracy by 15%.
Step 14: Build a Better Embedding Pipeline Later

Your V1 can embed the whole bullet text.

Your V2 can embed richer text:

Instead of:

Built ML models for fraud detection.

Embed:

Software Engineer
Python
Machine Learning
Fraud Detection

Built ML models for fraud detection.

This often produces stronger matches because the embedding has more context.

MVP Checklist
Database
 Store bullets individually
 Store projects individually
 Store coursework individually
Embeddings
 Generate embedding when item is created
 Save embedding
Job Matching
 Generate JD embedding
 Calculate cosine similarity
 Rank all items
Scoring
 Semantic similarity
 Skill overlap
 Recency bonus
Resume Generation
 Select top items
 Apply section quotas
 Rewrite selected bullets
 Export to PDF