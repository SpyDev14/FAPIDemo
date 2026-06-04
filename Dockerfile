FROM python:3.13.8-alpine

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./

COPY . .

EXPOSE 8000

CMD ["alembic", "upgrade", "head", "&&", "uv", "run", "fastapi", "dev", "--reload"]
