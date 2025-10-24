""" An API to query Odoo 
    Th. Estier - mars 2025
"""
from fastapi import FastAPI, Response
import xmlrpc.client
import ssl
from datetime import datetime
import requests
import pytz

context = ssl._create_unverified_context() # to avoid SSL certificate verification(if needed)
URL = "https://edu-heclausanne-saturne.odoo.com"
DB = "edu-heclausanne-saturne"
USER = "hang.yang@unil.ch"
PW = "hang.yang@unil.ch"
UID = False

def connect_odoo(hosturl, db, user, pw):
    "establish connection with odoo, return authentified UID "
    common = xmlrpc.client.ServerProxy(f'{hosturl}/xmlrpc/2/common', context=context )
    UID = common.authenticate(db, user, pw, {})
    if UID:
        return (UID, common)
    else:
        raise ConnectionError("bad username or password")
    
# initial setting
UID, c = connect_odoo(URL, DB, USER, PW)

app = FastAPI(
    title="Odoo API - Saturne",
    description="A simple API to interact with Odoo ERP system",
    version="1.0.0")


###
###  / g e t - s t a t u s
###
@app.get("/get-status", tags=["Status"])
async def hello():
    "get current odoo status and version"
    try:
        UID, common = connect_odoo(URL, DB, USER, PW)
        v = common.version()
        return {"Message" : f"user {UID} connected: Odoo version {v['server_version']} is waiting for requests on {DB}."}
    except Exception as err:
        return {"Message" : f"Problème de connexion au serveur {URL}, base:{DB}, utilisateur:{USER}",
                "Error" : f"Unexpected  {type(err)} : {err}"}

###
###  / c u s t o m e r s / a l l / l i s t
###
@app.get("/customers/all", tags=["Customers"])
async def get_all_customers():
    "get list of all customers, return dict of pairs (value:id, label:name)"
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=context)
    search_conditions = [ ('customer_rank','>',0) ]   # > 0 means is already customer, >= 0 means is potentially customer
    read_attributes = ['name', 'customer_rank']
    try:
        values = models.execute_kw(DB, UID, PW, 'res.partner', 'search_read', [search_conditions, read_attributes])
        return [{'value':c['id'], 
                 'label':c['name']} for c in values]
    except Exception as err:
        return {"Message" : f"Odoo error:",
                "Error" : f"Unexpected  {type(err)} : {err}"}

###
###  / c u s t o m e r s / c o m p a n i e s
###
@app.get("/customers/companies", tags=["Customers"])
async def get_companies_customers():
    "get list of campanies customers, return dict of pairs (value:id, label:name)"
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
@app.get("/customers/{cust_id}", tags=["Customers"])
async def get_customer_Info(cust_id: int):
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
###  / s a l e o r d e r s / { c u s t _ n a m e }
###
@app.get("/saleorders/by_name/{cust_name}", tags=["Sale Orders"])
def get_saleorders_by_customer_name(cust_name: str):
    "retrieve all sale orders of a particular customer, return complete values"
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=context)
    partner_ids = models.execute_kw(DB, UID, PW, 'res.partner', 'search', [[('name','ilike', cust_name)]])
    search_conditions = [('partner_id','=', partner_ids)]
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


###
###  / s a l e o r d e r s / { c u s t _ i d }
###
@app.get("/saleorders/by_id/{cust_id}", tags=["Sale Orders"])
async def get_saleorders_by_customer_id(cust_id: int):
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



###
###  / s a l e o r d e r s / q u o t a t i o n s / c o n f i r m /{ o r d e r _ n a m e }
###
@app.put("/saleorders/quotations/confirm/{order_name}", tags=["Sale Orders"])
def confirm_quotations(order_name: str):
    """
    Confirm a quote by its order name (e.g. 'S00001').
    """
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=context)
    try:
        # find the sale order by its name
        ids = models.execute_kw(
            DB, UID, PW,
            'sale.order', 'search',
            [[('name', '=', order_name)]]
        )
        if not ids:
            return {"message": f"Order {order_name} not found"}

        # Confirm the order
        models.execute_kw(DB, UID, PW, 'sale.order', 'action_confirm', [ids])
        return {"message": "Order confirmed successfully", "order_name": order_name, "ids": ids}
    except Exception as err:
        return {"message": "Odoo error", "error": f"Unexpected {type(err)} : {err}"}
    
###
###  / s a l e o r d e r s / q u o t a t i o n s / c a n c e l / { o r d e r _ n a m e }
###
@app.put("/saleorders/quotations/cancel/{order_name}", tags=["Sale Orders"])
def cancel_quotations(order_name: str):
    """
    Cancel a quote by its order name (e.g. 'S00001').
    Invisible: state not in ['draft' 'sent''sale'] or not id or locked
    """
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=context)
    try:
        # find the sale order by its name
        ids = models.execute_kw(
            DB, UID, PW,
            'sale.order', 'search',
            [[('name', '=', order_name)]]
        )
        if not ids:
            return {"message": f"Order {ids} not found"}

        # Cancel the order
        models.execute_kw(DB, UID, PW, 'sale.order', 'action_cancel', [ids])
        return {"message": "Order canceled successfully", "order_name": order_name, "ids": ids}
    except Exception as err:
        return {"message": "Odoo error", "error": f"Unexpected {type(err)} : {err}"}

###
###  / s a l e o r d e r s / i n v o i c e / c r e a t e /{ o r d e r _ n a m e }
###
@app.post("/saleorders/invoice/create/{order_name}", tags=["Sale Orders"])
async def create_invoice(order_name: str):
    """
    Create or request the creation of the invoice corresponding to a sales order.
    """
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=context, allow_none=True)

    try:
        order_id = models.execute_kw(
            DB, UID, PW,
            'sale.order', 'search',
            [[('name', '=', order_name)]]
        )
        if not order_id:
            return {"message": f"Order {order_id} not found"}
        # create the wizard record
        wizard_id = models.execute_kw(
            DB, UID, PW,
            'sale.advance.payment.inv', 'create',
            [{
                'advance_payment_method': 'delivered',
                'sale_order_ids': [(6, 0, order_id)]
            }]
        )
        
        # call the method to create the invoice
        invoice_action = models.execute_kw(
            DB, UID, PW,
            'sale.advance.payment.inv', 'create_invoices',
            [[wizard_id]]
        )
    except Exception as err:
        err_msg = str(err)
        # only ignore the error related to None serialization
        if "cannot marshal None" not in err_msg:
            # other errors are raised
            raise # unless the error is about None serialization, we proceed
    try:
        # first, get the invoice IDs linked to the sale order
        sale_order_data = models.execute_kw(
            DB, UID, PW,
            'sale.order', 'read',
            [order_id],
            {'fields': ['invoice_ids']}
        )

        invoice_ids = sale_order_data[0]['invoice_ids']

        if not invoice_ids:
            return {"sale_order_id": order_id, "invoice": None}

        # fetch invoice details
        invoices = models.execute_kw(
            DB, UID, PW,
            'account.move', 'read',
            [invoice_ids],
            {'fields': ['id', 'name', 'amount_total', 'state']}
        )

        # find the invoice with the maximum ID (latest created)
        max_invoice = max(invoices, key=lambda x: x['id'])

        return {
        "message": f"Invoice created successfully: ID={max_invoice['id']}, Name={max_invoice['name']}",
        "sale_order_id": order_id,
        "invoice": max_invoice     
    }

    except Exception as e:
        return {"error": str(e)}
    

###
###  / s a l e o r d e r s / d e l i v e r i e s / q u e r r y /{ o r d e r _ i d }
###
@app.get("/saleorders/delivery_date/querry/{order_id}", tags=["Sale Orders"])
async def handle_delivery_date(order_id: int):
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=context)
    """
    Get the scheduled delivery date of the current order
    """
    order = models.execute_kw(
        DB, UID, PW,
        'sale.order', 'read',
        [order_id],
        {'fields': ['name', 'commitment_date']}
    )
    utc_time_str = order[0]['commitment_date']
    if utc_time_str:
        # transform UTC to Europe/Zurich timezone
        utc = pytz.utc
        zurich = pytz.timezone('Europe/Zurich')
        utc_dt = utc.localize(datetime.strptime(utc_time_str, "%Y-%m-%d %H:%M:%S"))
        local_dt = utc_dt.astimezone(zurich)
        formatted_time = local_dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        formatted_time = None

    return {
        "order_id": order_id,
        "order_name": order[0]['name'],
        "scheduled_delivery_date": formatted_time
    }

###
###  / s a l e o r d e r s / d e l i v e r i e s / c o n f i r m ( r e j e c t )
###
@app.patch("/saleorders/delivery_date/confirm/{order_id,decision,new_date}", tags=["Sale Orders"])
async def decide_delivery(order_id: int, decision: str, new_date: datetime):
    """
    Confirm, reject, or propose a new delivery date for an order.
    action: "accept", "reject"
    new_date: ISO format (e.g. "2025-10-20 15:30:00") - required if action is "reject"
    """
    try:
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=context)
        if decision == "accept":
            return {"status": "accepted", "order_id": order_id}

        elif decision == "reject":
            if not new_date:
                return {"status": "error", "message": "new_date is required when rejecting", "order_id": order_id}
            
            # transform new_date to UTC
            dt_utc = new_date.astimezone(pytz.UTC)

            # update the commitment_date field
            result = models.execute_kw(
                DB, UID, PW,
                'sale.order', 'write',
                [[order_id], {'commitment_date': dt_utc.strftime("%Y-%m-%d %H:%M:%S")}]
            )

            if not result:
                return {"status": "error", "message": "Failed to update commitment_date", "order_id": order_id}

            return {
                "status": "rejected_and_date_updated",
                "order_id": order_id,
                "new_commitment_date": new_date
            }

        else:
            return {"status": "error", "message": "decision must be 'accept' or 'reject'", "order_id": order_id}

    except xmlrpc.client.Fault as e:
        return {"status": "error", "message": f"Odoo error: {e}", "order_id": order_id}
    except Exception as e:
        return {"status": "error", "message": str(e), "order_id": order_id}

###
###  / a c c o u n t i n g / i n v o i c e / b y _ s a l e o r d e r /{ o r d e r _ n a m e }
###
@app.get("/accounting/invoice/by_saleorder/{order_name}", tags=["Accounting"])
async def get_pdf_invoice(order_name: str):
    """
    Check all invoices of a sales order by its order name (e.g. 'S00001').
    """
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', context=context, allow_none=True)
    try:
        order_id = models.execute_kw(
            DB, UID, PW,
            'sale.order', 'search',
            [[('name', '=', order_name)]]
        )
        if not order_id:
            return {"message": f"Order {order_id} not found"}
            # first, get the invoice IDs linked to the sale order
        sale_order_data = models.execute_kw(
            DB, UID, PW,
            'sale.order', 'read',
            [order_id],
            {'fields': ['invoice_ids']}
        )

        invoice_ids = sale_order_data[0]['invoice_ids']

        if not invoice_ids:
            return {"sale_order_id": order_id, "invoice": None}

        # fetch invoice details
        invoices = models.execute_kw(
            DB, UID, PW,
            'account.move', 'read',
            [invoice_ids],
            {'fields': ['id', 'name', 'amount_total', 'state']}
        )
        return {
        "sale_order_id": order_id,
        "invoice": invoices    
        }
    except Exception as e:
        return {"error": str(e)}


###
###  / a c c o u n t i n g / i n v o i c e / g e t / p d f
###
@app.get("/accounting/invoice/get/pdf/{invoice_id}", tags=["Accounting"])
async def get_pdf_invoice(invoice_id: int):
    """
    Obtain a PDF version of an invoice.
    Example:http://127.0.0.1:8000/accounting/invoice/get/pdf/32
    """
    try:
        session = requests.Session()
        login_url = f"{URL}/web/session/authenticate"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "db": DB,
                "login": USER,
                "password": PW
            }
        }

        res = session.post(login_url, json=payload)
        if res.status_code != 200 or "result" not in res.json():
            return Response(
                content=f"Failed to log in to Odoo: {res.status_code}\n{res.text}",
                media_type="text/plain",
                status_code=500
            )

        # pdf report URL construction
        pdf_url = f"{URL}/report/pdf/account.report_invoice_with_payments/{invoice_id}"

        # send request for PDF with authenticated session
        pdf_res = session.get(pdf_url)
        if pdf_res.status_code != 200:
            return Response(
                content=f"Odoo returns an error: {pdf_res.status_code}\n{pdf_res.text}",
                media_type="text/plain",
                status_code=pdf_res.status_code
            )

        # pdf binary content return to browser
        return Response(
            content=pdf_res.content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=invoice_{invoice_id}.pdf"
            }
        )
    except Exception as e:
        return {"error": str(e)}

###
###  / p u r c h a s e o r d e r s / g e t / p d f
###
@app.get("/purchaseorders/get/pdf/{purchase_orders_id}", tags=["Purchase Orders"])
async def purchaseorders_get_pdf(purchase_orders_id: int):
    """
    Obtain a PDF version of an purchase order.
    Example:http://127.0.0.1:8000/purchaseorders/get/pdf/01
    """
    try:
        session = requests.Session()
        login_url = f"{URL}/web/session/authenticate"
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "db": DB,
                "login": USER,
                "password": PW
            }
        }

        res = session.post(login_url, json=payload)
        if res.status_code != 200 or "result" not in res.json():
            return Response(
                content=f"Failed to log in to Odoo: {res.status_code}\n{res.text}",
                media_type="text/plain",
                status_code=500
            )

        # construct PDF report URL
        pdf_url = f"{URL}/report/pdf/purchase.report_purchaseorder/{purchase_orders_id}"

        # send request for PDF with authenticated session
        pdf_res = session.get(pdf_url)
        if pdf_res.status_code != 200:
            return Response(
                content=f"Odoo returns an error: {pdf_res.status_code}\n{pdf_res.text}",
                media_type="text/plain",
                status_code=pdf_res.status_code
            )

        # pdf binary content return to browser
        return Response(
            content=pdf_res.content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=purchase_orders_{purchase_orders_id}.pdf"
            }
        )
    except Exception as e:
        return {"error": str(e)}
    


# Run the server
# Command to run: `fastapi dev my_odoo_api.py`