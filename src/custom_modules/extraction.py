import re
import pandas as pd
import hashlib

HEADER_LIST = ["timestamp","store","customer_name","basket_items","total_price","cash_or_card","card_number"]


def hash(s: str):
    # Adding unique IDs
    return str(int(hashlib.sha256(s.encode('utf-8')).hexdigest(), 16))[:10]


def clean_csv(df):
    # Deleting the cash_or_card and card_number columns
    del df["card_number"]
    del df["cash_or_card"]
    df.dropna(inplace=True)

    # Titling basket_items contents
    df['basket_items'] = df["basket_items"].str.title()
    return df


def process_csv(csv_file):
    try:
        # Importing and removing sensitive data and null values
        df = pd.read_csv(csv_file, names=HEADER_LIST)
        df = clean_csv(df)

        # Seperating basket_items
        df["item"] = df["basket_items"].apply(lambda x: x.split(","))
        df = df.explode("item")
        df = create_price_product_columns(df)
        del df["item"]

        df["order_id"] = (df["timestamp"] + df["store"] + df["customer_name"]).apply(lambda x: hash(x))


        # Change the format to DD-MM-YYYY HH:MM:SS
        df['timestamp'] = df['timestamp'].apply(lambda x: pd.Timestamp(x).strftime("%d-%m-%Y %X"))
        
        # Deleting the customer_name and basket_items columns
        del df["customer_name"]
        del df["basket_items"]
        
        # Rearrange order_id to front
        cols = df.columns.tolist()
        cols = cols[-1:] + cols[:-1]
        df = df[cols]

    except KeyError as e:
        print(f"ERROR: KeyError - {e}")

    
    return df


def create_price_product_columns(df):
    df["product_name"] = df["item"].apply(lambda x: re.findall(r"[a-zA-Z -]+", x)[0].rstrip("- ").strip())
    df["price"] = df["item"].apply(lambda x: re.findall(r"[0-9]+.[0-9]+", x)[0])
    return df
