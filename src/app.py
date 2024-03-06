from __future__ import annotations

import os

import aws_cdk as cdk
import aws_cdk.aws_apigatewayv2 as apigw
import aws_cdk.aws_apigatewayv2_integrations as integrations
import aws_cdk.aws_ecr_assets as ecr_assets
import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_s3 as s3
from constructs import Construct
from openai import OpenAI
from utils.config import settings


class Stack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # if settings.vpc_id:
        #     vpc = ec2.Vpc.from_lookup(self, f"{id}-vpc", vpc_id=settings.VPC_ID)
        # else:
        #     vpc = ec2.Vpc(self, "vpc")

        bucket = s3.Bucket(
            self,
            'bucket',
            removal_policy=(
                cdk.RemovalPolicy.DESTROY
                if settings.STAGE == 'dev'
                else cdk.RemovalPolicy.RETAIN
            ),
        )

        # Create a Lambda function
        thread_runner_lambda_function = _lambda.Function(
            self,
            'thread-runner-lambda',
            code=_lambda.Code.from_asset_image(
                directory='src/lambda',
                cmd=['thread_runner.handler'],
                platform=ecr_assets.Platform.LINUX_AMD64,
            ),
            handler=_lambda.Handler.FROM_IMAGE,
            runtime=_lambda.Runtime.FROM_IMAGE,
            environment={
                # TOOD: use secretsmanager
                'OPENAI_API_KEY': settings.OPENAI_API_KEY,
                'OPENAI_EMBEDDING_MODEL': settings.OPENAI_EMBEDDING_MODEL,
                'LANCEDB_DATA_PATH': settings.LANCEDB_DATA_PATH,
                'BUCKET_NAME': bucket.bucket_name,
            },
            timeout=cdk.Duration.seconds(10 * 60),
            memory_size=1024,
        )

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        assistants = [
            assistant
            for assistant in client.beta.assistants.list()
            if assistant.name == settings.OPENAI_ASSISTANT_NAME
        ]
        if not assistants:
            raise Exception(f'Assistant {settings.OPENAI_ASSISTANT_NAME} not found')
        assistant = assistants[0]

        api_lambda_function = _lambda.Function(
            self,
            'api-lambda',
            code=_lambda.Code.from_asset_image(
                directory='src/lambda',
                cmd=['main.handler'],
                platform=ecr_assets.Platform.LINUX_AMD64,
            ),
            handler=_lambda.Handler.FROM_IMAGE,
            runtime=_lambda.Runtime.FROM_IMAGE,
            environment={
                # TOOD: use secretsmanager
                'OPENAI_API_KEY': settings.OPENAI_API_KEY,
                'OPENAI_ASSISTANT_ID': assistant.id,
                'THREAD_RUNNER_LAMBDA_ARN': thread_runner_lambda_function.function_arn,
                'STAGE': settings.STAGE,
            },
            timeout=cdk.Duration.seconds(60),
            memory_size=1024,
        )

        api_lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=['lambda:InvokeFunction'],
                resources=[thread_runner_lambda_function.function_arn],
            ),
        )
        thread_runner_lambda_function.grant_invoke(api_lambda_function)

        # Grant the Lambda function read/write permissions to the bucket
        bucket.grant_read_write(thread_runner_lambda_function)

        # Create an API Gateway
        api = apigw.HttpApi(
            self,
            f'api-gateway-{settings.STAGE}',
            default_integration=integrations.HttpLambdaIntegration(
                'lambda-integration',
                api_lambda_function,
            ),
        )

        # Output the API Gateway URL
        cdk.CfnOutput(self, 'api_endpoint', value=api.url)  # type: ignore
        cdk.CfnOutput(self, 'bucket_name', value=bucket.bucket_name)  # type: ignore


CDK_DEFAULT_REGION = os.environ.get('CDK_DEFAULT_REGION')
CDK_DEFAULT_ACCOUNT = os.environ.get('CDK_DEFAULT_ACCOUNT')


app = cdk.App()

env = cdk.Environment(region=CDK_DEFAULT_REGION, account=CDK_DEFAULT_ACCOUNT)


stack_name = f'wb-agrifoods-data-lab-{settings.STAGE}'.lower()

stack = Stack(app, stack_name, env=env)

for key, value in {
    'Project': 'agrifoods-data-lab',
    'Owner': settings.OWNER,
    'Client': 'world-bank',
    'Stage': settings.STAGE,
}.items():
    cdk.Tags.of(app).add(key, value, apply_to_launched_instances=True)

app.synth()
