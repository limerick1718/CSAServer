
run postgresql for the first time
```
cd CSAServer
docker run --name postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=postgres -d -p 5432:5432 -v db-data:/var/lib/postgresql/data postgres
```

if cannot connect, change to
```
host all all all trust
```
in `db-data/pg_hba.conf`

run postgresql after the first time
```
docker start postgres
```

run application
```bash
docker run -it --rm --name csaserver -p 1992:1992 --network host -v .:/app -w /app csaserver bash start.sh
```