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
def get_recipes(
    category: str | None = None,
    search: str | None = None,
    limit: int | None = None
    ):
    conditions = []
    params = []

    if category:
        conditions.append("category = %s")
        params.append(category)
    if search:
        conditions.append("name ILIKE %s")
        params.append(f"%{search}%")
    if limit is not None:
        if limit < 1:
            raise HTTPException(
                status_code=422, detail="You must enter a number greater than zero"
                )
        add_limit = " LIMIT %s"
        params.append(limit)
    else: 
        add_limit = ""

    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)
    else:
        where_clause = ""

    query = "SELECT * FROM recipes" + where_clause + " ORDER BY id" + add_limit

    cursor = connection.cursor()
    cursor.execute(query, params)
    recipes = cursor.fetchall()
    return format_recipes(recipes)

@app.delete("/recipe/{id}")
def delete_recipe(id: int):
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM recipes "
        "WHERE id = %s",
        (id,)
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Recipe not found")
    else:
        connection.commit()
    return {"message": "Recipe deleted successfully"}

@app.put("/recipe/{id}")
def change_recipe(id: int, recipe: Recipe):
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE recipes "
        "SET name = %s, description = %s, category = %s "
        "WHERE id = %s",
        (recipe.name, recipe.description, recipe.category, id,)
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Recipe not found")
    else:
        connection.commit()
    return {
        "id": id,
        "name": recipe.name,
        "description": recipe.description,
        "category": recipe.category
    }
