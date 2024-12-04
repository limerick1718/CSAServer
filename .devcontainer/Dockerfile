FROM python:3.10
LABEL authors="jiakun"

COPY requirements.txt /tmp/requirements.txt

RUN DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get -yq install aapt \
    && pip install -r /tmp/requirements.txt

#uvicorn main:app --host 0.0.0.0 --port 1992
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "1992"]