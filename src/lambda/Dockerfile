FROM public.ecr.aws/lambda/python:3.11

ENV LANG en_US.utf8

WORKDIR ${LAMBDA_TASK_ROOT}

COPY . ${LAMBDA_TASK_ROOT}

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt -t ${LAMBDA_TASK_ROOT}

# TODO: verify this CMD allows devs to run
# the API locally, while also allowing the
# Dockerfile to be used to build the Lambda
# correctly
CMD [ "uvicorn",  "main:app", "--reload" ]
