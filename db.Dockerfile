FROM postgres:17.5

RUN apt-get update && apt-get install -y postgresql-server-dev-15 build-essential git && \
git clone --depth 1 https://github.com/pgvector/pgvector && \
cd pgvector && \
make && make install && \
cd .. && rm -rf pgvector && \
apt-get remove -y build-essential git && \
apt-get autoremove && apt-get clean

ENV POSTGRES_USER=myuser
ENV POSTGRES_PASSWORD=1234
ENV POSTGRES_DB=rag_db

EXPOSE 5432
