import mysql.connector.pooling

# Database connection pooling
dbconfig = {
    "host": "202.53.78.150",
    "user": "Munisyam",
    "password": "vardaa@123",
    "database": "vasp"
}

connection_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,  # Reduced pool size to prevent exceeding max connections
    pool_reset_session=True,
    **dbconfig
)

def execute_query(query, params=None, commit=False):
    connection = None
    cursor = None
    try:
        connection = connection_pool.get_connection()
        cursor = connection.cursor(buffered=True)

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if query.strip().lower().startswith('select'):
            results = cursor.fetchall()
        else:
            if commit:
                connection.commit()
            results = None

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        raise  # Re-raise the exception for better debugging

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()  # Ensure connection is always returned to the pool

    return results
