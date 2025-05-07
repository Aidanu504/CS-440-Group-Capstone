FROM python

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

EXPOSE 5000

VOLUME ["/app/data"]

ENV FLASK_APP=app.py \
    FLASK_ENV=development \
    FLASK_DEBUG=1 \
    SQLALCHEMY_DATABASE_URI=sqlite:////app/data/retail.db

CMD ["python", "app.py"]
