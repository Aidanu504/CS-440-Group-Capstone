# CS-440-Group-Capstone

This is our final capstone project for CS 440 group 2. Design Document available to be downloaded in above files. 

## Features

- Manage customers, products and suppliers (relational DB)
- Store and retrieve order data (Document DB)
- Record payment and sales data (Graph DB)
- Cach product data to track popularity (Cache)

## Databases utilized

- Relational Database: SQLite - stores customer, product, and supplier data.
- Document Database: MongoDB - handles order data. 
- Graph Database: Neo4j - models relationships such as payments and sales 
- Cache: Redis - stores cached product data 

## Setup 

1. prerequisites

- Docker 
- Python

2. Running the project
```
docker-compose up --build
```

This will start the four containers:
- Flask (localhost:5000)
- MongoDB (locahost:27017)
- Redis (localhost:6379)
- Neo4j (localhost:7474)

3. Navigate to localhost:5000 to interact with the UI!

## Database operations
Functions for each query are below
- sqlite:
list_products,
get_products,
add_products,
update_products,
create_order,
get_orders,
popular_products,
product_history,
list_suppliers,
add_suppliers,
list_customers,
add_customers

- Neo4j:
update_product,
create_order,
make_payment,
get_payment,
popular_products,
sales_analytics,
product_history

- Redis:
Get_product,
popular_products

- mongoDB:
create_order,
get_orders

## Testing
These can either be tested wihtin the UI or there is an attached postman collection to run each query. This collection is grouped into each type of database so you can easily test each one.  
