FROM python:3.9
WORKDIR /app
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "gui.py"]
