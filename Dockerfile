FROM python:3.9

WORKDIR /

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY xiamon xiamon
COPY config config
CMD ["python", "xiamon/xiamon.py", "--config", "userconfig"]