from fastapi import FastAPI

from src.routes.v1.routes import router

app = FastAPI()
app.include_router(router=router)