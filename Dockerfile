# 1. Usamos una versión ligera de Python 3.11
FROM python:3.11-slim

# 2. Establecemos la carpeta de trabajo dentro del servidor
WORKDIR /app

# 3. Instalamos dependencias del sistema necesarias para Flet/UI (opcional pero recomendado)
RUN apt-get update && apt-get install -y \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# 4. Copiamos el archivo de librerías primero para aprovechar la caché
COPY requirements.txt .

# 5. Instalamos las librerías (Flet, etc.)
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copiamos todo el código de tu carpeta actual al servidor
COPY . .

# 7. Exponemos el puerto 8080 (estándar de la nube)
EXPOSE 8080

# 8. Comando para arrancar Flet en modo WEB para que el mundo lo vea
CMD ["flet", "run", "--web", "--port", "8080"]