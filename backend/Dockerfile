FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000
WORKDIR /service
COPY requirements.txt requirements-postgres.txt ./
ARG INSTALL_POSTGRES=false
RUN python -m pip install -r requirements.txt \
    && if [ "$INSTALL_POSTGRES" = "true" ]; then python -m pip install -r requirements-postgres.txt; fi \
    && useradd --create-home --uid 10001 appuser
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser rules ./rules
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/health',timeout=2).close()"]
CMD ["python", "-m", "app.run"]
