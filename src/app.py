import pandas as pd
import boto3
import json
from src.custom_modules.extraction import (
    create_price_product_columns,
    process_csv,
    clean_csv,
)
from io import StringIO
import shortuuid

s3 = boto3.client("s3")

def s3_upload(df):
    tag = shortuuid.ShortUUID().random(length=4)
    bucket = "team1-s3-clean-csv" 
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    s3_resource = boto3.resource("s3")
    s3_resource.Object(bucket, f"clean_{tag}.csv").put(Body=csv_buffer.getvalue())
    print("uploaded csv to s3")


def extract_transform_function(event, context):
    print(f"Recieved event: {event}")

    receipt_handle = event["Records"][0]["receiptHandle"]
    message = json.loads(event["Records"][0]["body"])
    key = message["Records"][0]["s3"]["object"]["key"]
    bucket = message["Records"][0]["s3"]["bucket"]["name"]

    print(f"Detected {key} uploaded in {bucket}")

    response = s3.get_object(Bucket=bucket, Key=key)
    csv_file = response["Body"]

    print("retrieved object")

    try:
        df = process_csv(csv_file)
        print("processed csv")
    except ValueError as e:
        print(f"Error processing csv: {e}")
        return

    s3_upload(df)

    print("Extract/Transform END")
