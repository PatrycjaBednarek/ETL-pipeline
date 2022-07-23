sql_staging_table = ''' CREATE temp TABLE csv_staging{} (
                                    s_order_id varchar(17),
                                    s_datetime timestamp NOT NULL,
                                    s_store varchar(70) NOT NULL,
                                    s_total_price decimal(7,2) NOT NULL,
                                    s_product_name varchar(100) NOT NULL,
                                    s_price decimal(7,2) NOT NULL
                                    );
                                    '''
sql_products_table = ''' CREATE TABLE IF NOT EXISTS products (
                                    product_id      INT primary key generated always as identity,
                                    product_name    VARCHAR(100) NOT NULL,
                                    product_price   DECIMAL(7,2) NOT NULL
                                    );
                                    '''

sql_transactions_staging_table = ''' CREATE temp TABLE transactions_staging{} (
                                    order_id  VARCHAR(17),
                                    product_id      INT NOT NULL,
                                    product_quantity INT,
                                    product_price   DECIMAL(7,2) NOT NULL
                                    );
                                    '''

sql_transactions_table = ''' CREATE TABLE IF NOT EXISTS transactions (
                                    order_id  VARCHAR(17),
                                    product_id      INT NOT NULL,
                                    product_quantity INT,
                                    transaction_price   DECIMAL(7,2) NOT NULL,
                                    CONSTRAINT fk_products
                                        FOREIGN KEY(product_id)
                                            REFERENCES products(product_id),
                                    CONSTRAINT fk_order
                                        FOREIGN KEY(order_id)
                                            REFERENCES orders(order_id)
                                    );
                                    '''

sql_orders_table = ''' CREATE TABLE IF NOT EXISTS orders (
                                    order_id      VARCHAR(17) PRIMARY KEY NOT NULL,
                                    store_name    VARCHAR(70) NOT NULL,
                                    datetime	  timestamp NOT NULL,
                                    total_amount_spent DECIMAL(7,2) NOT NULL
                                    );
                                    '''
