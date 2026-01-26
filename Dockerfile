FROM python:3.12
WORKDIR /app

COPY . .

RUN pip install --upgrade pip \
 && pip install pipenv \
 && pip install -r tools/tafsir_gui/requirements.txt \
 && pip install -r tools/tafsir_gui/tests/requirements.txt \
 && cd Tafsir \
 && pipenv install

ENTRYPOINT ["python", "main.py"]
