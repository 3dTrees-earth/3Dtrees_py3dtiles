FROM python:3.10-slim

# Install system dependencies for lazrs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    py3dtiles \
    "laspy[lazrs,laszip]" \
    pyproj \
    numpy \
    tqdm

WORKDIR /src
COPY ./src /src

CMD ["python", "run.py", "--help"]

