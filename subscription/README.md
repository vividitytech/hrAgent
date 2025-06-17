## Payment

Use stripe for payment.

## How it works

create db/tables -> run payment.py -> make payment


## Pre-requisites

### Install mysql

1. install mysql will be a little different for different systems, if you use ubuntu
    `sudo apt install mysql-server`
    `sudo service mysql status`
2. python interface: `pip install mysql-connector-python==9.2.0`

### Install stripe (trial account)
1. `pip install stripe`
2.  create account and get following keys
```
STRIPE_PUBLISHABLE_KEY=
STRIPE_SECRET_KEY=
```


## How to run payment service

### Run mysql server
run in the comomend line: `sudo service mysql start`
set the db username and password
create .env and add environmental variables

### Create database
Try `python create_db.py`

### Create tables
Try `python create_tables.py`


### Create subscriptions
Run `python create_subscription_types.py`
This will different subscriptions such as pay as you go, monthly and yearly subscriptions.


### Run the service
Try `python payment.py` to start the server.


## Demo and debug
Try `python test_payment.py`

