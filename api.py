from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import os
from pathlib import Path

app = FastAPI(title="BIMigrator API")

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Store migration status in memory (replace with database in production)
migrations = {}

class MigrationStatus(BaseModel):
    status: str
    progress: float
    message: str
    input_file: Optional[str] = None
    download_url: Optional[str] = None
    created_at: Optional[str] = None

@app.get("/api/migration/check-file/{filename}")
async def check_file_exists(filename: str):
    file_path = Path("input") / filename
    return {"exists": file_path.exists()}

@app.post("/api/migration/upload")
async def upload_workbook(file: UploadFile = File(...)):
    if not file.filename.endswith(('.twb', '.twbx')):
        raise HTTPException(400, "Only .twb or .twbx files are allowed")
    
    # Create unique ID for this migration
    migration_id = str(uuid.uuid4())
    
    # Ensure input and output directories exist
    input_dir = Path("input")
    output_dir = Path("output") / migration_id
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded file to input directory, overwriting if exists
    file_path = input_dir / file.filename
    content = await file.read()
    
    # Save with error handling
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(500, f"Failed to save file: {str(e)}")
    
    # Initialize migration status with timestamp
    from datetime import datetime
    migrations[migration_id] = MigrationStatus(
        status="uploaded",
        progress=0,
        message=f"File uploaded successfully to {file_path.name}. Ready to start migration.",
        created_at=datetime.now().isoformat(),
        input_file=str(file_path)
    )
    
    return {"migration_id": migration_id}

@app.post("/api/migration/start/{migration_id}")
async def start_migration(migration_id: str):
    if migration_id not in migrations:
        raise HTTPException(404, "Migration not found")
    
    if migrations[migration_id].status != "uploaded":
        raise HTTPException(400, "Migration is not in a valid state to start")
    
    try:
        # Update status to processing
        migrations[migration_id].status = "processing"
        migrations[migration_id].message = "Starting migration..."
        
        # Get file paths
        input_file = migrations[migration_id].input_file
        output_dir = Path("output") / migration_id
        
        if not Path(input_file).exists():
            raise HTTPException(404, "Input file not found")
        
        # TODO: Process the workbook asynchronously
        # Temporarily simulate processing
        update_migration_status(migration_id, 100, "Migration completed successfully")
        
        # Create zip file of output
        # TODO: Implement zip creation of output files
        
        migrations[migration_id].status = "completed"
        migrations[migration_id].progress = 100
        migrations[migration_id].message = "Migration completed successfully"
        migrations[migration_id].download_url = f"/api/migration/download/{migration_id}"
        return {"status": "success", "message": "Migration completed successfully"}
        
    except Exception as e:
        error_msg = f"Migration failed: {str(e)}"
        migrations[migration_id].status = "error"
        migrations[migration_id].progress = 0
        migrations[migration_id].message = error_msg
        
        # Log error for debugging
        import logging
        logging.error(f"Migration {migration_id} failed: {str(e)}")
        
        # Clean up input file on error
        try:
            if Path(file_path).exists():
                Path(file_path).unlink()
            if input_dir.exists() and not any(input_dir.iterdir()):
                input_dir.rmdir()
        except Exception as cleanup_error:
            logging.error(f"Failed to clean up after error: {str(cleanup_error)}")
        
        raise HTTPException(500, error_msg)
    
    return {"migration_id": migration_id}

@app.get("/api/migration/status/{migration_id}")
async def get_migration_status(migration_id: str):
    if migration_id not in migrations:
        raise HTTPException(404, "Migration not found")
    return migrations[migration_id]

@app.get("/api/migration/download/{migration_id}")
async def download_migration(migration_id: str):
    if migration_id not in migrations:
        raise HTTPException(404, "Migration not found")
    
    if migrations[migration_id].status != "completed":
        raise HTTPException(400, "Migration not completed")
    
    output_dir = Path("output") / migration_id
    if not output_dir.exists():
        raise HTTPException(404, "Migration files not found")
    
    # TODO: Create and return zip file of output directory
    # For now, return a sample file
    return {"message": "Download endpoint - implement zip file creation"}

def update_migration_status(migration_id: str, progress: float, message: str):
    """Update the status of a migration"""
    if migration_id in migrations:
        migrations[migration_id].progress = progress
        migrations[migration_id].message = message
