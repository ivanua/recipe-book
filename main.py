from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from db import connection

class Recipe(BaseModel):
    name: str
    description: str | None = None
    category: str 
    
app = FastAPI()

#HELPER FUNCTIONS
def format_recipes(recipes):
    result = [] 
    for recipe in recipes:
        recipe_dict = {"id": recipe[0], "name": recipe[1], "description": recipe[2], "category": recipe[3]}
        result.append(recipe_dict)
    return result

@app.get("/")
def root():
    return {"message": "Welcome to RecipeBook"}

@app.post("/recipe/")
async def create_recipe(recipe: Recipe):
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO recipes(name, description, category) "
        "VALUES(%s, %s, %s) "
        "RETURNING id",
        (recipe.name, recipe.description, recipe.category)
    )
    recipe_id = cursor.fetchone()[0]
    connection.commit()

    return {
        "id": recipe_id,
        "name": recipe.name,
        "description": recipe.description,
        "category": recipe.category

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
        "description": recipe[2],
        "category": recipe[3]
    }

@app.get("/recipes/")
def get_recipes(category: str | None = None):
    if category is None:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT * " 
            "FROM recipes "
            "ORDER BY id"
        )
        recipes = cursor.fetchall()
        return format_recipes(recipes)
    else:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT * "
            "FROM recipes "
            "WHERE category = %s",
            (category,)
        )
        recipes = cursor.fetchall()
        return format_recipes(recipes)
