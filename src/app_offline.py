import pandas as pd
import psycopg2
import psycopg2.extras
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from custom_modules.extraction import initial_extract_products_price, create_price_product_columns
import re
import shortuuid
# from custom_modules.sqltables import *

HEADER_LIST = ["timestamp","store","customer_name","basket_items","total_price","cash_or_card","card_number"]

def clean_csv(df):
    del df["card_number"]
    del df["customer_name"]
    df.dropna(inplace=True)
    df['basket_items'] = df["basket_items"].str.title() 
    return df

def process_csv(csv_file):
    try:
        # importing and removing sensitive data and null values
        df = pd.read_csv(csv_file, names = HEADER_LIST)
        df = clean_csv(df)

        # seperating basket_items
        df["item"] = df["basket_items"].apply(lambda x: x.split(","))
        df = df.explode("item")
        df = create_price_product_columns(df)

        # replacing index with a  unique id (UUID4)
        df = df.reset_index()
        for id in df['index'].unique():
            df.loc[df['index'] == id, 'index'] = shortuuid.ShortUUID().random(length=6)

    except KeyError as e:
        print(f"ERROR: KeyError - {e}")
    
    return df


#Connect to posgreSQL database
# try:
#     connection = psycopg2.connect(
#     host = "localhost",
#     database = "cafe_db",
#     user = "root",
#     password = "password"
#     )
#     print ("\n***Connected to Cafe's database***")
# except psycopg2.DatabaseError as e:
#     print(f"\nERROR: Unable to successfully connect to Database.\n{e}")
#     print("Please check database connection. Quitting application...\n")
#     quit()

# cursor = connection.cursor()
# cursor.execute(create_products_table)
# cursor.execute(create_basket_items)
# cursor.execute(create_transactions_table)
# cursor.execute(create_clean_data_table)          

df_chesterfield = process_csv("team1-project\example_transactions.csv")
print(df_chesterfield)

# # returning product price and names
print("\n___CREATING PRODUCT PRICE AND NAMES DATAFRAME___\n")
df_products = initial_extract_products_price(df_chesterfield)
print("\n___PRODUCT PRICE AND NAME DATAFRAME CREATED, RESULT: ___\n")
print(df_products)


# automatically insert any new products into sql. If df_Products is updated, so will sql table. If not, nothing.
# for row in df_products.itertuples():
#     sql = f"INSERT INTO products_table (product_name, product_price) SELECT \'{row.product}\', {row.price} WHERE NOT EXISTS (SELECT * FROM products_table WHERE product_name = \'{row.product}\');"
#     cursor.execute(sql)
# connection.commit()

print("____PROGRAM ENDED____")