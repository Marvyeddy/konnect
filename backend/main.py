from fastapi import FastAPI

version = "v1"

app = FastAPI(
    title="konnect",
    description="A consumer-to-consumer (C2C) platform enabling direct exchange of goods, services, or information.",
    version=version,
    redoc_url=f"/api/{version}/redoc",
    docs_url=f"/api/{version}/docs",
    contact={
        "name": "Marvelous Anyatonwu",
        "url": "https://linkedin.com/in/anyatonwumarvelous",
        "email": "anyatonwumarvelous32@gmail.com",
    },
    license_info={"name": "MIT License", "url": "https://opensource.org/licenses/MIT"},
)


@app.get("/")
async def root():
    return {"message": "Welcome to the konnect app"}
