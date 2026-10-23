from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from psycopg.errors import UniqueViolation
from db import connection
from typing import Any
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()
def hash_password(password: str) -> str:
    return password_hash.hash(password)

class Recipe(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    category: str 

    @field_validator("name", mode="before")
    @classmethod
    def validate_name_not_blank(cls, v: Any) -> str:
    # Проверяем, пустая ли строка после удаления пробелов
        if isinstance(v, str):

            if not v.strip():
                raise ValueError("Имя не может состоять только из пробелов или быть пустым")
        else:
            return v
    # Возвращаем значение (можно вернуть v.strip(), чтобы автоматически убрать лишние пробелы по краям)
        return v.strip()
message_error = "Password must contain at least one lowercase and one uppercase letters and one digit"
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    password_confirm: str

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must contain at least 8 characters")
        if not any("a" <= char <= "z" for char in value):
            raise ValueError(message_error)
        if not any("A" <= char <= "Z" for char in value):
            raise ValueError(message_error)
        if not any("0" <= char <= "9" for char in value):
            raise ValueError(message_error)
        return value

    @model_validator(mode="after")
    def check_passwords(self):
        if self.password == self.password_confirm:
            return self
        else:
            raise ValueError("Пароли не совпадают") 

class UserLogin(BaseModel):
    email: EmailStr
    password: str

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
    limit: int = Query(gt=0,  le=25, default=10),
    offset: int = Query(ge=0, default=0)
    ):
    
    if search  is not None:
        search = search.strip() or None
    conditions = []
    params = []
    params_for_count = []

    if category:
        conditions.append("category = %s")
        params.append(category)
        params_for_count.append(category)

    if search:
        conditions.append("name ILIKE %s")
        params.append(f"%{search}%")
        params_for_count.append(f"%{search}%")
    
    add_limit = " LIMIT %s"
    params.append(limit)
   


    db_offset = "OFFSET %s"
    params.append(offset)

    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)
    else:
        where_clause = ""

    query = "SELECT * FROM recipes" + where_clause + " ORDER BY id" + add_limit + " " + db_offset
    query_for_count = "SELECT COUNT(*) FROM recipes " + where_clause 

    cursor = connection.cursor()
    cursor.execute(query, params)
    recipes = cursor.fetchall()
    cursor.execute(query_for_count, params_for_count)
    total = cursor.fetchone()[0]
    has_next = total > offset + limit
    has_prev = 0 < offset < total
    return {"items": format_recipes(recipes), "total": total, "has_prev": has_prev, "has_next": has_next}


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

@app.post("/auth/register")
def create_user(user: UserCreate):
    hashing_pass = hash_password(user.password)
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash ) "
            "VALUES (%s, %s, %s) "
            "RETURNING id",
            (user.username, user.email, hashing_pass,)
        )
        user_id = cursor.fetchone()[0]
        connection.commit()
        return {
            "id": user_id,
            "username": user.username,
            "email": user.email
        }
    except UniqueViolation:
        connection.rollback()
        raise HTTPException(status_code=409, detail="username or email already exists")

@app.post("/auth/login")
def login_user(user: UserLogin):
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, username, email, password_hash "
        "FROM users "
        "WHERE email = %s",
        (user.email,)
    )
    result = cursor.fetchone()
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not password_hash.verify(user.password, result[3]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"message": "login successful", "user_id": result[0], "username": result[1], "email": result[2]}
