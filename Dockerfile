FROM python:3.11-slim-buster

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 5000

ENV FLASK_APP=server
ENV FLASK_ENV=production

CMD ["sh", "-c", "gunicorn -w $(python -c 'import multiprocessing as mp; print(mp.cpu_count() // 2 + 1)') -k gevent -b 0.0.0.0:5000 server:app"]
