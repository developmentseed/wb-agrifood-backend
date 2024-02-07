from __future__ import annotations

import os

import aws_cdk as cdk
import aws_cdk.aws_apigatewayv2 as apigw
import aws_cdk.aws_apigatewayv2_integrations as integrations
import aws_cdk.aws_ecr_assets as ecr_assets
import aws_cdk.aws_lambda as _lambda
import aws_cdk.aws_s3 as s3
from constructs import Construct
from utils.config import settings

# import aws_cdk.aws_ec2 as ec2


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
        handler = _lambda.Function(
            self,
            'lambda',
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
                'OPENAI_MODEL': settings.OPENAI_MODEL,
                'OPENAI_EMBEDDING_MODEL': settings.OPENAI_EMBEDDING_MODEL,
                'OPENAI_ASSISTANT_NAME': settings.OPENAI_ASSISTANT_NAME,
                'LANCEDB_DATA_PATH': settings.LANCEDB_DATA_PATH,
                'BUCKET_NAME': bucket.bucket_name,
            },
            timeout=cdk.Duration.seconds(60),
            memory_size=1024,
        )

        bucket.grant_read_write(handler)

        # Create an API Gateway
        api = apigw.HttpApi(
            self,
            'api-gateway',
            default_integration=integrations.HttpLambdaIntegration(
                'lambda-integration',
                handler,
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
