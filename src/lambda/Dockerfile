FROM public.ecr.aws/lambda/python:3.11

ENV LANG en_US.utf8

WORKDIR ${LAMBDA_TASK_ROOT}

COPY . ${LAMBDA_TASK_ROOT}

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt -t ${LAMBDA_TASK_ROOT}
