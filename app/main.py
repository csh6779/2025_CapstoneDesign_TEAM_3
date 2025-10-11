from fastapi import FastAPI
from app.api.v1.endpoints.user import user

app = FastAPI(
  title="CAPSTONE API",
  version="1.0.0",
)

app.include_router(user.router, prefix="/v1/users", tags=["Users"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI Backend!"}
