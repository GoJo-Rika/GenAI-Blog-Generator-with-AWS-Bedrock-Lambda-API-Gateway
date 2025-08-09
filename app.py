import json
import traceback
from datetime import datetime

import boto3
import botocore.config


def blog_generate_using_bedrock(blogtopic: str) -> str:
    """
    Generates blog content using AWS Bedrock and the Llama 3 model.

    Args:
        blogtopic: The topic for the blog post.

    Returns:
        The generated blog content as a string, or an empty string on failure.

    """
    # Define the prompt for the model.
    prompt = f"Human: Write a 200 words blog on the topic {blogtopic}"

    # Embed the prompt in Llama 3's specific instruction format for optimal performance.
    formatted_prompt = f"""
    <|begin_of_text|><|start_header_id|>user<|end_header_id|>
    {prompt}
    <|eot_id|>
    <|start_header_id|>assistant<|end_header_id|>
    """

    # Specify the model ID for Llama 3 8B Instruct.
    model_id = "meta.llama3-8b-instruct-v1:0"

    # Define the request body with model parameters.
    # max_gen_len: The maximum number of tokens to generate.
    # temperature: Controls the randomness of the output. Lower is more deterministic.
    # top_p: Nucleus sampling parameter to control the diversity of the output.
    native_request = {"prompt": formatted_prompt, "max_gen_len": 512, "temperature": 0.5, "top_p": 0.9}

    try:
        # Initialize the Bedrock runtime client with a specified region and configuration.
        # The config includes a read timeout and retry attempts for robustness.
        bedrock = boto3.client("bedrock-runtime", region_name="us-east-1",
                               config=botocore.config.Config(read_timeout=300, retries={"max_attempts": 3}))

        # Convert the native request dictionary to a JSON string.
        request = json.dumps(native_request)

        # Invoke the model with the specified model ID and the request body.
        response = bedrock.invoke_model(modelId=model_id, body=request)

        # Read the streaming response body.
        response_content = response["body"].read()

        # Parse the JSON response data.
        response_data = json.loads(response_content)
        print(response_data)

        # Extract the generated text from the response.
        blog_details = response_data["generation"]
        return blog_details

    except Exception as e:
        # Log any errors that occur during blog generation.
        print(f"Error generating the blog:{e}")
        return ""


def save_blog_details_s3(s3_key: str, s3_bucket: str, generate_blog: str) -> None:
    """
    Saves the generated blog content to an S3 bucket.

    Args:
        s3_key: The key (file path) for the object in S3.
        s3_bucket: The name of the S3 bucket.
        generate_blog: The blog content to save.

    """
    # Initialize the S3 client.
    s3 = boto3.client("s3")

    try:
        # Use put_object to upload the generated blog content to S3.
        s3.put_object(Bucket=s3_bucket, Key=s3_key, Body=generate_blog)
        print("Code saved to s3")

    except Exception as e:
        # Log any errors that occur during the S3 save operation.
        print(f"Error when saving the code to s3: {e!s}")
        print(f"Error details: {traceback.format_exc()}") # For more detailed logging


def lambda_handler(event: dict, context) -> dict:
    """
    The main handler for the AWS Lambda function.

    Args:
        event: The event dictionary from API Gateway.
        context: The runtime information from AWS Lambda.

    Returns:
        A dictionary with a status code and a JSON-formatted body.

    """
    # The event body from API Gateway is a string, so it needs to be parsed as JSON.
    event = json.loads(event["body"])

    # Extract the blog topic from the event.
    blogtopic = event["blog_topic"]

    # Call the function to generate the blog post.
    generate_blog = blog_generate_using_bedrock(blogtopic=blogtopic)

    # If a blog was successfully generated, save it to S3.
    if generate_blog:

        # Get the current time to create a unique file name.
        current_time = datetime.now().strftime("%H%M%S")

        # Define the S3 key (file path) for the output file.
        s3_key = f"blog-output/{current_time}.txt"

        # The name of the S3 bucket (should be an environment variable in a real-world app).
        s3_bucket = "aws-bedrock-demo-course"   # IMPORTANT: Make sure this matches your S3 bucket name.

        # Call the function to save the blog to S3.
        save_blog_details_s3(s3_key, s3_bucket, generate_blog)

        # Return a success response.
        return {"statusCode": 200, "body": json.dumps("Blog Generation is completed")}

    # If no blog was generated, log it and return a corresponding message.
    print("No blog was generated")
    return {"statusCode": 200, "body": json.dumps("No blog was generated")}
