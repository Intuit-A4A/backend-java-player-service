FROM python:3.11
LABEL authors="efeinstein"

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install \
      --yes \
      --no-install-recommends \
      ca-certificates curl python3 && \
    curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:${PATH}"
COPY . /usr/local/a4a_model
WORKDIR /usr/local/a4a_model
RUN poetry config virtualenvs.create false
RUN poetry install
WORKDIR /usr/local/a4a_model/a4a_model
EXPOSE 8657
ENTRYPOINT ["python", "server.py"]