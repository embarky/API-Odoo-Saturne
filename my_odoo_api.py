""" An API to query Odoo 
    Th. Estier - mars 2025
"""
from fastapi import FastAPI
import xmlrpc.client
import ssl

context = ssl._create_unverified_context() # to avoid SSL certificate verification
URL = "https://edu-heclausanne-saturne.odoo.com"
DB = "edu-heclausanne-saturne"
USER = "hang.yang@unil.ch"
PW = "hang.yang@unil.ch"
UID = False

def connect_odoo(hosturl, db, user, pw):
    "establish connection with odoo, return authentified uid "
    common = xmlrpc.client.ServerProxy(f'{hosturl}/xmlrpc/2/common', context=context)
    uid = common.authenticate(db, user, pw, {})
    if uid:
        return (uid, common)
    else:
        raise ConnectionError("bad username or password")
    
# initial setting
UID, c = connect_odoo(URL, DB, USER, PW)

app = FastAPI()

###
###  / g e t - s t a t u s
###
@app.get("/get-status")
async def hello():
    "get current odoo status and version"
    try:
        uid, common = connect_odoo(URL, DB, USER, PW)
        v = common.version()
        return {"Message" : f"user {uid} connected: Odoo version {v['server_version']} is waiting for requests on {DB}."}
    except Exception as err:
        return {"Message" : f"Problème de connexion au serveur {URL}, base:{DB}, utilisateur:{USER}",
                "Error" : f"Unexpected  {type(err)} : {err}"}

###
###  / c u s t o m e r s / l i s t
###
@app.get("/customers/list")
async def get_all_customers():
    "get list of all customers, return dict of pairs (value:id, label:name)"
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=context)
    search_conditions = [('is_company','=', True), 
                         ('customer_rank','>',0) ]   # > 0 means is already customer, >= 0 means is potentially customer
    read_attributes = ['name', 'customer_rank']
    try:
        values = models.execute_kw(DB, UID, PW, 'res.partner', 'search_read', [search_conditions, read_attributes])
        return [{'value':c['id'], 
                 'label':c['name']} for c in values]
    except Exception as err:
        return {"Message" : f"Odoo error:",
                "Error" : f"Unexpected  {type(err)} : {err}"}

###
###  / c u s t o m e r s / { c u s t _ i d }
###
@app.get("/customers/{cust_id}")
async def get_customer_data(cust_id: int):
    "get relevant data of a particular customer, return name, email, city, country"
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=context)
    read_attributes = {'fields': ['name',
                                  'email',
                                  'city',
                                  'country_id', 
                                  'comment']}
    try:
        cust_info = models.execute_kw(DB, UID, PW, 'res.partner', 'read', [cust_id], read_attributes)
        return cust_info
    except Exception as err:
        return {"Message" : f"Odoo error:",
                "Error" : f"Unexpected  {type(err)} : {err}"}


###
###  / s a l e o r d e r s / { c u s t _ i d }
###
@app.get("/saleorders/{cust_id}")
async def get_customer_so(cust_id: int):
    "retrieve all sale orders of a particular customer, return complete values"
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=context)
    search_conditions = [('partner_id','=', cust_id) ]  
    so_attributes = ['name', 
                     'state', 
                     'create_date', 
                     'amount_total',
                     'order_line']   # list of ids of order lines composing this so
    try:
        so_values = models.execute_kw(DB, UID, PW, 'sale.order', 'search_read', [search_conditions, so_attributes])
        for so in so_values:
            solin_attributes = {'fields':['name', 
                                          'product_uom_qty', 
                                          'price_unit', 
                                          'price_total']}
            solin_values = models.execute_kw(DB, UID, PW, 'sale.order.line', 'read', [so['order_line']], solin_attributes)
            so['order_line'] = solin_values  # replace array of line ids by array of retrieved line values
        return so_values
    except Exception as err:
        errmsg = str(err)
        return {"Message" : f"Odoo error:",
                "Error" : f"Unexpected  {type(err)} : {errmsg}"}

# Run the server
# Command to run: `fastapi dev my_odoo_api.py`