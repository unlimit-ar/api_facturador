# Usa una imagen base de Python
FROM python:3.9


# Establece el directorio de trabajo en /app
WORKDIR /app

# Copia el archivo de requerimientos y lo instala
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt


RUN git clone --branch RSA-fix --single-branch https://github.com/pablopadulles/pyafipws.git
RUN pip install pyafipws/. 

# Expone el puerto 8000
EXPOSE 8000

# Comando para correr la aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
