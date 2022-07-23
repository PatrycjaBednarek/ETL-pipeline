from logging import exception
import pandas as pd
import psycopg2
import psycopg2.extras
import os
import boto3
import json
import shortuuid
from src.custom_modules.extraction import (
    create_price_product_columns,
    process_csv,
    clean_csv,
)
from src.custom_modules.sqltablenames import *

SSM = "team1-redshift-secrets"

def get_db_credentials(credential_name):
    ssm = boto3.client("ssm")
    response = ssm.get_parameter(Name=credential_name)
    creds_string = response["Parameter"]["Value"]
    db, user, password, host, port = creds_string.split(",")
    return db, user, password, host, port


def connect_to_db():
    try:
        db, user, password, host, port = get_db_credentials(SSM)
        connection = psycopg2.connect(
            f"dbname={db} user={user} password={password} host={host} port={port}"
        )
        return connection
    except psycopg2.DatabaseError as e:
        print(f"\nERROR: Unable to successfully connect to Database.\n{e}")
        print("Please check database connection. Quitting application...\n")
        quit()


print("Trying to connect...")
connection = connect_to_db()
cursor = connection.cursor()
print("Connection successful.")


def create_tables(tag):
    try:
        cursor.execute(sql_staging_table.format(tag))
        print("Staging table created.")
        cursor.execute(sql_products_table)
        print("Products table checked.")
        cursor.execute(sql_orders_table)
        print("Orders table checked.")
        cursor.execute(sql_transactions_table)
        print("Transactions table checked.")
        cursor.execute(sql_transactions_staging_table.format(tag))
        print("Transactions staging table created.")
        connection.commit()
        print("committed tables")
    except Exception as e:
        print(f"Error occurred during table creation: {e}")


def loading_to_tables(bucket, key, tag):
    print("loading_to_tables started.")

    try:
        sql = f"COPY csv_staging{tag} FROM 's3://{bucket}/{key}' iam_role 'arn:aws:iam::370445109106:role/service-role/AmazonRedshift-CommandsAccessRole-20220708T124422' IGNOREHEADER 1 DELIMITER ',' TIMEFORMAT 'auto';"
        cursor.execute(sql)
        connection.commit()
        print("CSV copied to staging table successfully.")

        sql = f"INSERT INTO products (product_name, product_price) SELECT DISTINCT s_product_name, s_price FROM csv_staging{tag} WHERE NOT EXISTS (SELECT * FROM products WHERE product_name = csv_staging{tag}.s_product_name);"
        cursor.execute(sql)
        connection.commit()
        print("Insert into products completed successfully.")

        sql = f"""INSERT INTO orders (order_id, store_name, datetime, total_amount_spent)
        SELECT DISTINCT s_order_id, s_store, s_datetime, s_total_price
        FROM csv_staging{tag}
        WHERE NOT EXISTS (SELECT * FROM orders WHERE order_id = s_order_id);"""
        cursor.execute(sql)
        connection.commit()
        print("Insert to orders completed successfully.")

        sql = f"INSERT INTO transactions_staging{tag} (order_id, product_price, product_id) SELECT s_order_id, s_price, product_id FROM products, csv_staging{tag} WHERE products.product_name = csv_staging{tag}.s_product_name"
        cursor.execute(sql)
        connection.commit()
        print(f"Insert to transactions staging{tag} completed successfully.")

        sql = f"""UPDATE transactions_staging{tag} t SET product_quantity = QTY FROM (SELECT ORDER_ID, PRODUCT_ID, COUNT(*) AS QTY FROM transactions_staging{tag} GROUP BY ORDER_ID, PRODUCT_ID) b
            WHERE t.order_id = b.order_id
            and t.product_id = b.product_id;"""
        cursor.execute(sql)
        print("Transactions staging updated successfully.")
        connection.commit()

        sql = f"""INSERT INTO transactions SELECT STG.order_id, STG.product_id, count(STG.product_quantity), sum(STG.product_price) FROM transactions_staging{tag} as STG LEFT OUTER JOIN transactions TGT ON STG.ORDER_ID = TGT.ORDER_ID AND STG.PRODUCT_ID = TGT.PRODUCT_ID WHERE TGT.ORDER_ID IS NULL GROUP BY (STG.order_id, STG.product_id)"""
        cursor.execute(sql)
        connection.commit()
        print("Transactions completed successfully")
    except Exception as e:
        print(f"Error occurred during data loading: {e}")


def load_function(event, context):

    print(f"Recieved event: {event}")

    try:
        receipt_handle = event["Records"][0]["receiptHandle"]
        message = json.loads(event["Records"][0]["body"])
        key = message["Records"][0]["s3"]["object"]["key"]
        bucket = message["Records"][0]["s3"]["bucket"]["name"]
    except KeyError as e:
        print(f"Key Error whilst pulling from S3 event: {e}")
        return

    print(f"Detected {key} uploaded in {bucket}")

    tag = shortuuid.ShortUUID().random(length=5)
    print(f"Tag: {tag}")

    create_tables(tag)

    loading_to_tables(bucket, key, tag)

    print("Load ended")
