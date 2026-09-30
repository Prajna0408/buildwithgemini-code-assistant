"""Seed script to populate Firestore with initial code snippets for code-assistant.

IMPORTANT: PROJECT_ID is hardcoded as a string per Firestore guidance.
Do NOT use google.auth.default() or GOOGLE_CLOUD_PROJECT environment variable.
"""

from google.cloud import firestore

FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-84f054ebc9cd"

SEED_SNIPPETS = [
    {
        "id": "async-retry-decorator",
        "title": "Python Async Retry Decorator with Exponential Backoff",
        "language": "python",
        "category": "Async / Concurrency",
        "description": "A robust decorator for retrying async functions upon failure with configurable attempts and backoff delay.",
        "code": '''import asyncio
import functools

def async_retry(retries=3, delay=1.0, backoff=2.0):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(1, retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == retries:
                        raise e
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator
''',
        "tags": ["asyncio", "decorator", "resilience", "python"],
    },
    {
        "id": "fastapi-cors-middleware",
        "title": "FastAPI CORS Middleware Configuration",
        "language": "python",
        "category": "API / Web Frameworks",
        "description": "Configures Cross-Origin Resource Sharing (CORS) in FastAPI to allow frontend apps to talk to backend API.",
        "code": '''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
''',
        "tags": ["fastapi", "cors", "middleware", "web"],
    },
    {
        "id": "git-conventional-commit-validator",
        "title": "Conventional Commit Message Regex Validator",
        "language": "python",
        "category": "Git / DevOps",
        "description": "Validates whether a given commit message adheres to the Conventional Commits specification.",
        "code": '''import re

CONVENTIONAL_COMMIT_PATTERN = r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-z0-9_\-\.]+\))?: .+$"

def validate_commit_message(msg: str) -> bool:
    return bool(re.match(CONVENTIONAL_COMMIT_PATTERN, msg.strip()))
''',
        "tags": ["git", "conventional-commits", "regex", "devops"],
    },
]

def seed_firestore():
    db = firestore.Client(project=FIRESTORE_PROJECT_ID)
    collection_ref = db.collection("snippets")
    
    print(f"Seeding Firestore collection 'snippets' in project: {FIRESTORE_PROJECT_ID}...")
    for item in SEED_SNIPPETS:
        doc_ref = collection_ref.document(item["id"])
        doc_ref.set(item)
        print(f"  ✓ Seeded snippet: {item['id']} ({item['title']})")
    
    print("Done seeding Firestore!")

if __name__ == "__main__":
    seed_firestore()
