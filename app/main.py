import uvicorn
from fastapi import FastAPI

from app.api.v1.api import api_router

app = FastAPI(
    title="FireFlow API",
    description="Backend API for Job Search and Candidate Tracking Application",
    version="1.0.0"
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "welcome to Hireflow API"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)