**Install Dependencies:**
  
EtherTime depends on Python3.11 or greater and requires a Django compatible database (see below for setting up EtherTime with PostgreSQL). Additionally, PTP/NTP vendor packages need to be installed for each vendor that will be evaluated. For resource contention tests, Stress-NG and iPerf are required. For automatic power failure emulation, Tuya smart power strips are required.

```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

Install time synchronization packages:

_Note: Installing Chrony may cause systemd-timesyncd to be uninstalled_

```bash
sudo apt update
sudo apt install linuxptp chrony ptpd
```

Install resource contention tools:

```bash
sudo apt update
sudo apt install iperf stress-ng
```

Finally, Python libraries need to be installed.

```bash
pip3 install -r requirements.txt
```

### Configuring the Database (PostgreSQL)

EtherTime relies on Django as its database abstraction layer and to serve graphics and data tables. To start profiling, a database that is accessible from all nodes in the testbed is required. We use PostgreSQL but any other supported database should also be compatible.

**Note**: only one database is required for the entire cluster.

To set up PostgreSQL for use with EtherTime, follow these steps:

#### Install PostgreSQL

First, install PostgreSQL on your system.

On Ubuntu:

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

On CentOS/RHEL:

```bash

sudo yum install postgresql-server postgresql-contrib
sudo postgresql-setup initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### Configure PostgreSQL

Start the PostgreSQL service and ensure it runs at startup.

On Ubuntu, Debian and CentOS/RHEL::

```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### Create a PostgreSQL Database and User

Log in to the PostgreSQL shell as the postgres user:

```bash
sudo -i -u postgres
psql
```

Create a new database and user for EtherTime:

```sql
CREATE DATABASE ethertimedb;
CREATE USER ethertimeuser WITH PASSWORD 'ethertimepassword';
```
**Note:** Username, database name and password can be named freely and should be chosen apprioriately.

Set the correct privileges:

```sql
ALTER ROLE ethertimeuser SET client_encoding TO 'utf8';
ALTER ROLE ethertimeuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE ethertimeuser SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE ethertimedb TO ethertimeuser;
```


#### Configure EtherTime Django Settings

Edit your EtherTime project's settings.py file to configure the database settings. Make sure to use your own host, database names, users and passwords.

```python

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ethertimedb',
        'USER': 'ethertimeuser',
        'PASSWORD': 'ethertimepassword',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

#### Apply Migrations

To set up the database for use with EtherTime, we need to import the provided database schema.

```bash
python manage.py makemigrations
python manage.py migrate
```

#### Verify the Setup

Run the Django development server to verify that everything is configured correctly.

```bash
python manage.py runserver
```

Visit http://127.0.0.1:8000/ in your web browser. If everything is set up correctly, EtherTime should now be running using your PostgreSQL database, and your system will soon be ready to start benchmarking.

**Additional Configuration**

For production deployments, you might want to perform additional configuration such as setting up a firewall, configuring SSL, and optimizing the PostgreSQL settings. Refer to the official Django documentation and PostgreSQL documentation for more detailed information.
