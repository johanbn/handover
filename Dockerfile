FROM python:3.12

WORKDIR /app

# Install uv
RUN pip install uv

# Put the virtualenv somewhere not covered by the bind mount
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

# Copy only lock/config first for caching
COPY pyproject.toml uv.lock .python-version ./

# Install deps at build time into /opt/venv
RUN uv sync --frozen

# Copy the rest
COPY . .

EXPOSE 8888

CMD ["uv", "run", "jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]