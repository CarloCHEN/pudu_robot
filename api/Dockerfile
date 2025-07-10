# FROM python:3.10-alpine3.18

# # WORKDIR /app

# COPY . .

# RUN pip install -r requirements.txt

# EXPOSE 5000

# ENV PYTHONUNBUFFERED=1

# CMD ["python" ,"app.py"]

FROM python:3.8

WORKDIR /usr/src/app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r ./requirements.txt

COPY api/app.py .
RUN mkdir src
# copy the src folder's contents to the container
COPY src/foxx_api ./src
COPY src/pudu_api ./src


# Command to run the FastAPI app using uvicorn
CMD ["uvicorn", "app:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]