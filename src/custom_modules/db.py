import psycopg2
from .sqltablenames import *

#########
#use connection pool
################

#connection_pool = pool.SimpleConnectionPool(3, 10, database="team1_project", user="team1", password="Team1pass", host="redshiftcluster-bnfuhsmtsjms.c3ixzwdqenpm.eu-west-1.redshift.amazonaws.com")
# app.py needs with connection_pool.getconn() as connection:
#         with connection.cursor() as cursor:
#                  cursor.execute()
