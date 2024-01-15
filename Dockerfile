FROM python:3.11

WORKDIR /home_inv

COPY ./requirements.txt /home_inv/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /home_inv/requirements.txt

COPY ./main.py /home_inv/
COPY ./schemas.py /home_inv/
COPY ./models.py /home_inv/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
