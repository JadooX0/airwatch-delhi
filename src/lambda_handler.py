"""AWS Lambda entry point: run the pipeline and publish data.json to S3.

Environment variables:
  BUCKET            (required) S3 bucket that hosts the dashboard
  KEY               (optional) object key, default "data.json"
  MODE              (optional) "live" (default) or "synthetic"
  OPENAQ_API_KEY    (optional) real ground sensors
  FIRMS_MAP_KEY     (optional) NASA FIRMS fire detections
Suggested: runtime Python 3.12 / x86_64, handler lambda_handler.handler, memory 3008 MB (or your account's max),
timeout 5 min. Model training takes roughly 15-60 s.
"""
import os

# Keep native thread pools small so they behave inside Lambda's 2-vCPU sandbox (must be set before numpy/sklearn import)
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import json  # noqa: E402

import boto3  # noqa: E402  (provided by the Lambda runtime)

import pipeline  # noqa: E402

s3 = boto3.client("s3")


def handler(event, context):
    out = "/tmp/data.json"
    res = pipeline.run(mode=os.getenv("MODE", "live"), out_path=out)
    s3.upload_file(out, os.environ["BUCKET"], os.getenv("KEY", "data.json"),
                   ExtraArgs={"ContentType": "application/json", "CacheControl": "max-age=300"})
    return {"statusCode": 200, "body": json.dumps({
        "stations": len(res["stations"]), "city_now": res["city"]["pm25_now"],
        "city_peak": res["city"]["peak"]})}
