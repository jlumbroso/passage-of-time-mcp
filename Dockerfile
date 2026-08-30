FROM python:3.12-slim

WORKDIR /app

# Install pipenv
RUN pip install pipenv

# Copy Pipfile first to cache deps
COPY Pipfile Pipfile.lock ./

RUN pipenv install --deploy --ignore-pipfile

COPY . .

EXPOSE 8000

CMD ["pipenv", "run", "python", "passage_of_time_mcp.py"]