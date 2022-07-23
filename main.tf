terraform {
  required_version = ">= 0.13"
}
# ------------------------------------------------------------------------------
# CONFIGURE OUR AWS CONNECTION AND STS ASSUME ROLE
# ------------------------------------------------------------------------------
provider "aws" {
  region = "eu-west-1"
}
# ------------------------------------------------------------------------------
# CONFIGURE REMOTE STATE
# ------------------------------------------------------------------------------
terraform {
  backend "s3" {
    bucket = "team1-delon7-tf-state"
    key    = "team1-terraform.tfstate"
    region = "eu-west-1"
  }
}

################################################################################
# Lambda role
################################################################################
resource "aws_iam_role" "lambda_function_role" {
  name               = "team1-lambda-etl-role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}
resource "aws_iam_role_policy_attachment" "s3_full_access" {
  role       = aws_iam_role.lambda_function_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}
resource "aws_iam_role_policy_attachment" "lambda_execution_role" {
  role       = aws_iam_role.lambda_function_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
resource "aws_iam_role_policy_attachment" "redshift_full_access" {
  role       = aws_iam_role.lambda_function_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonRedshiftFullAccess"
}
resource "aws_iam_role_policy_attachment" "lamdba_vpc_access" {
  role       = aws_iam_role.lambda_function_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}
resource "aws_iam_role_policy_attachment" "full_sqs_access" {
  role       = aws_iam_role.lambda_function_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSQSFullAccess"
}
resource "aws_iam_role_policy_attachment" "ssm_read_access" {
  role       = aws_iam_role.lambda_function_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess"
}
# ################################################################################
# # Lambda function, layers and invocation
# ################################################################################
#### Extract transform lambda
resource "aws_lambda_function" "lambda_etl" {
  filename      = "src.zip"
  function_name = "team1-lambda-etl"
  handler       = "src/app.extract_transform_function"
  role          =  aws_iam_role.lambda_function_role.arn
  runtime       = "python3.8"
  memory_size   = 248
  timeout       = 30
  layers = [
    "arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-python38-aws-psycopg2:1",
    "arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p38-pandas:4",
    "arn:aws:lambda:eu-west-1:370445109106:layer:shortuuid-python38:1"
  ]
  source_code_hash = filebase64sha256("src.zip")

}
########### Second lambda function (load lambda)
resource "aws_lambda_function" "lambda_load" {
  filename      = "src.zip"
  function_name = "team1-load-lambda"
  handler       = "src/app2.load_function"
  role          =  aws_iam_role.lambda_function_role.arn
  runtime       = "python3.8"
  memory_size   = 248
  timeout       = 180
  layers = [
    "arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-python38-aws-psycopg2:1",
    "arn:aws:lambda:eu-west-1:770693421928:layer:Klayers-p38-pandas:4",
    "arn:aws:lambda:eu-west-1:370445109106:layer:shortuuid-python38:1"
  ]
  source_code_hash = filebase64sha256("src.zip")

}

# ################################################################################
# # Setting up SQS
# ################################################################################

# SQS Raw Data Queue
resource "aws_sqs_queue" "queue" {
  name = "team1-raw-csv-queue"
  visibility_timeout_seconds = 200
  receive_wait_time_seconds = 1
  policy = <<EOF
{
  "Version": "2008-10-17",
  "Id": "__default_policy_ID",
  "Statement": [
    {
      "Sid": "__owner_statement",
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": "SQS:*",
      "Resource": "arn:aws:sqs:eu-west-1:370445109106:team1-raw-csv-queue"
    }
  ]
}
EOF
}

#sqs clean csv queue
resource "aws_sqs_queue" "clean_csv_queue" {
  name = "team1-clean-csv-queue"
  visibility_timeout_seconds = 200
  receive_wait_time_seconds = 1
  policy = <<EOF
{
  "Version": "2008-10-17",
  "Id": "__default_policy_ID",
  "Statement": [
    {
      "Sid": "__owner_statement",
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": "SQS:*",
      "Resource": "arn:aws:sqs:eu-west-1:370445109106:team1-clean-csv-queue"
    }
  ]
}
EOF
}

#dlq
resource "aws_sqs_queue" "team1_dlq_raw" {
  name = "team1-dlq-raw"
  visibility_timeout_seconds = 200
  receive_wait_time_seconds = 1
  policy = <<EOF
{
  "Version": "2008-10-17",
  "Id": "__default_policy_ID",
  "Statement": [
    {
      "Sid": "__owner_statement",
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": "SQS:*",
      "Resource": "*"
    }
  ]
}
EOF
}

# ################################################################################
# # S3 bucket and event notification and Queue!
# ################################################################################

# S3 raw transactions data bucket
resource "aws_s3_bucket" "transactions_bucket" {
  bucket = "team1-store-transactions-data-raw"
}

# S3 raw event notification
resource "aws_s3_bucket_notification" "transaction_data_bucket_notification" {
  bucket = aws_s3_bucket.transactions_bucket.id
  queue {
    queue_arn = aws_sqs_queue.queue.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".csv"
  }
}

# Event source from sqs
resource "aws_lambda_event_source_mapping" "s3_raw_sqs_trigger" {
  event_source_arn = aws_sqs_queue.queue.arn
  function_name    = aws_lambda_function.lambda_etl.arn
  batch_size = 1
}

# S3_clean_csv bucket
resource "aws_s3_bucket" "clean_bucket" {
  bucket = "team1-s3-clean-csv"
}

# S3 clean event notification
resource "aws_s3_bucket_notification" "clean_data_bucket_notification" {
  bucket = aws_s3_bucket.clean_bucket.id
  queue {
    queue_arn = aws_sqs_queue.clean_csv_queue.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".csv"
  }
}

# Event source from sqs
resource "aws_lambda_event_source_mapping" "s3_clean_sqs_trigger" {
  event_source_arn = aws_sqs_queue.clean_csv_queue.arn
  function_name    = aws_lambda_function.lambda_load.arn
  batch_size = 1
}
