from fastapi import FastAPI
from app.api.agencies import router as agencies_router

app = FastAPI(title="eCFR Analyzer", description="API for analyzing the Electronic Code of Federal Regulations")

@app.get("/")
async def root():
    return {"message": "Welcome to eCFR Analyzer API"}

# Include the agencies router
app.include_router(agencies_router, prefix="/api/agencies", tags=["agencies"])

@app.get("/api/agencies/{agency_id}/documents")
async def get_agency_documents(agency_id: str):
    """Retrieve all documents for a given agency and store them in a database"""
    # TODO: Implement document retrieval and storage
    return {"message": f"Documents for agency {agency_id} will be returned here"}

@app.post("/api/agencies/{agency_id}/process")
async def process_agency_documents(agency_id: str):
    """Process documents for agency - compute metrics for all documents"""
    # TODO: Implement document processing
    return {"message": f"Processing documents for agency {agency_id}"}