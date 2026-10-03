import psycopg

connection = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="recipe_book",
    user="postgres",
    password=""
)

print("Database connected!")
