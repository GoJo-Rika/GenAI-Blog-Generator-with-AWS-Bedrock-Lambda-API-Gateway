import json
import traceback
from datetime import datetime

import boto3
import botocore.config


def blog_generate_using_bedrock(blogtopic: str) -> str:
    # Define the prompt for the model.
    prompt = f"Human: Write a 200 words blog on the topic {blogtopic}"

    # Embed the prompt in Llama 3's instruction format.
    formatted_prompt = f"""
    <|begin_of_text|><|start_header_id|>user<|end_header_id|>
    {prompt}
    <|eot_id|>
    <|start_header_id|>assistant<|end_header_id|>
    """

    model_id = "meta.llama3-8b-instruct-v1:0"

    native_request = {"prompt": formatted_prompt, "max_gen_len": 512, "temperature": 0.5, "top_p": 0.9}

    try:
        bedrock = boto3.client("bedrock-runtime", region_name="us-east-1", 
                               config=botocore.config.Config(read_timeout=300, retries={"max_attempts": 3}))

        request = json.dumps(native_request)
        response = bedrock.invoke_model(modelId=model_id, body=request)

        response_content = response["body"].read()
        response_data = json.loads(response_content)
        print(response_data)

        blog_details = response_data["generation"]
        return blog_details

    except Exception as e:
        print(f"Error generating the blog:{e}")
        return ""


def save_blog_details_s3(s3_key: str, s3_bucket: str, generate_blog: str) -> None:
    s3 = boto3.client("s3")

    try:
        s3.put_object(Bucket=s3_bucket, Key=s3_key, Body=generate_blog)
        print("Code saved to s3")

    except Exception as e:
        print(f"Error when saving the code to s3: {e!s}")
        print(f"Error details: {traceback.format_exc()}") # For more detailed logging


def lambda_handler(event: dict, context) -> dict:
    # TODO implement
    event = json.loads(event["body"])
    blogtopic = event["blog_topic"]

    generate_blog = blog_generate_using_bedrock(blogtopic=blogtopic)

    if generate_blog:
        current_time = datetime.now().strftime("%H%M%S")
        s3_key = f"blog-output/{current_time}.txt"
        s3_bucket = "aws-bedrock-demo-course"
        save_blog_details_s3(s3_key, s3_bucket, generate_blog)
        return {"statusCode": 200, "body": json.dumps("Blog Generation is completed")}

    print("No blog was generated")
    return {"statusCode": 200, "body": json.dumps("No blog was generated")}