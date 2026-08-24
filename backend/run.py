import uvicorn
from app.core.db import init_db
from seed import seed_database

if __name__ == "__main__":
    # Initialize database
    init_db()
    
    # Seed database with initial data
    seed_database()
    
    # Run the application
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

    