from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from db import connection

class Recipe(BaseModel):
    name: str
    description: str | None = None
    
app = FastAPI()

@app.get("/")
def root():
    return {"message": "Welcome to RecipeBook"}

@app.post("/recipe/")
async def create_recipe(recipe: Recipe):
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO recipes(name, description) "
        "VALUES(%s, %s) "
        "RETURNING id",
        (recipe.name, recipe.description)
    )
    recipe_id = cursor.fetchone()[0]
    connection.commit()

    return {
        "id": recipe_id,
        "name": recipe.name,
        "description": recipe.description
    }

@app.get("/recipe/{id}")
def recipe(id: int):
    cursor = connection.cursor()

    cursor.execute(
        "SELECT *" \
        " FROM recipes" \
        " WHERE id = %s",
        (id,)
    )
    recipe = cursor.fetchone()

    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    return{
        "id": recipe[0],
        "name": recipe[1],
        "description": recipe[2]
    }