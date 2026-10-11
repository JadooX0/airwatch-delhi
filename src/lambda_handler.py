
import os


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
