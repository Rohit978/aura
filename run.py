#!/usr/bin/env python3

import uvicorn
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Initialize database before starting server
try:
    from src.database.models import init_database
    print("Initializing database...")
    init_database()
    print("✓ Database ready")
except Exception as e:
    print(f"⚠ Database initialization: {e}")
    # Continue anyway - database might already exist

if __name__ == "__main__":
    print("=" * 60)
    print("AI Music Recommendation System")
    print("=" * 60)
    print("\nStarting API server...")
    print("API will be available at: http://localhost:8000")
    print("Interactive docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop\n")
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

