from fastapi import FastAPI
from pydantic import BaseModel

class Recipe(BaseModel):
    name: str
    description: str | None = None
    
app = FastAPI()

@app.get("/")
def root():
    return {"message": "Welcome to RecipeBook"}

@app.post("/recipe/")
async def create_recipe(recipe: Recipe):
    return recipe