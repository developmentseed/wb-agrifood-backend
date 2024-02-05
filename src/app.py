from __future__ import annotations

import os

import aws_cdk as cdk
import aws_cdk.aws_apigatewayv2 as apigw
import aws_cdk.aws_apigatewayv2_integrations as integrations
import aws_cdk.aws_ecr_assets as ecr_assets
import aws_cdk.aws_lambda as _lambda
from constructs import Construct
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict
# import aws_cdk.aws_ec2 as ec2


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra='ignore')
    VPC_ID: str = ''
    STAGE: str
    OWNER: str
    OPENAI_ASSISTANT_NAME: str
    OPENAI_API_KEY: str
    OPENAI_MODEL: str
    OPENAI_EMBEDDING_MODEL: str


settings = Settings(
    # Comment explaining  why the ignore is needed
    # need it's own noqa because of flake8's line length
    # restrictions :(
    # ignore NOTE: https://github.com/blakeNaccarato/pydantic/blob/c5a29ef77374d4fda85e8f5eb2016951d23dac33/docs/visual_studio_code.md?plain=1#L260-L272 # noqa
    _env_file=os.environ.get('ENV_FILE', '.env'),  # type: ignore
)


class Stack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # if settings.vpc_id:
        #     vpc = ec2.Vpc.from_lookup(self, f"{id}-vpc", vpc_id=settings.VPC_ID)
        # else:
        #     vpc = ec2.Vpc(self, "vpc")

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
            },
            timeout=cdk.Duration.seconds(60),
            memory_size=1024,
        )

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
        cdk.CfnOutput(self, 'api_endpoint', value=api.url)


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
