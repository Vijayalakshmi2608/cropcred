from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from database import get_connection, init_db, seed_db

app = Flask(__name__)
CORS(app, resources={r'/api/*': {'origins': '*'}})


def ok(data, status=200):
    return jsonify({'success': True, 'data': data}), status


def fail(message, status=400):
    return jsonify({'success': False, 'error': message}), status


def rows(query, params=()):
    connection = get_connection()
    result = [dict(row) for row in connection.execute(query, params).fetchall()]
    connection.close()
    return result


def row(query, params=()):
    connection = get_connection()
    value = connection.execute(query, params).fetchone()
    connection.close()
    return dict(value) if value else None


def farmer_payload(item):
    if not item: return None
    item['primary_crops'] = item['primary_crops'].split(',') if isinstance(item.get('primary_crops'), str) else item.get('primary_crops', [])
    item['initials'] = ''.join(part[0] for part in item['name'].split()[:2]).upper()
    return item


def harvest_payload(item):
    if not item: return None
    item['expected_price_label'] = f"₹{item['expected_price']:g}/{item['unit']}"
    try:
        item['harvest_date_label'] = datetime.fromisoformat(item['harvest_date']).strftime('%d %b %Y') if 'T' in item['harvest_date'] else datetime.strptime(item['harvest_date'], '%Y-%m-%d').strftime('%d %b %Y')
    except ValueError:
        item['harvest_date_label'] = item['harvest_date']
    return item


def listing_payload(item):
    if not item: return None
    item['price_label'] = f"₹{item['price_per_unit']:g}/{item['unit']}"
    item['harvest_date_label'] = datetime.strptime(item['harvest_date'], '%Y-%m-%d').strftime('%d %b %Y')
    item['available'] = item['quantity_available']
    item['verification'] = 'Verified harvest' if item['verification_status'] == 'VERIFIED' else item['verification_status'].title()
    return item


def order_payload(item):
    if not item: return None
    item['amount_label'] = f"₹{item['total_amount']:g}"
    item['wallet'] = 'Awaiting Solana transaction'
    return item

@app.get('/api/health')
def health():
    return jsonify({'status': 'ok'})

@app.get('/api/farmers')
def get_farmers():
    return ok([farmer_payload(x) for x in rows('SELECT * FROM farmers ORDER BY created_at')])

@app.get('/api/farmers/<farmer_id>')
def get_farmer(farmer_id):
    item = farmer_payload(row('SELECT * FROM farmers WHERE id=?', (farmer_id,)))
    return ok(item) if item else fail('Farmer not found', 404)

@app.post('/api/farmers')
def create_farmer():
    data = request.get_json(silent=True) or {}
    required = ['id', 'name', 'location', 'primary_crops', 'farm_size']
    if any(not data.get(key) for key in required): return fail('Name, location, primary crops, farm size, and id are required.')
    connection = get_connection()
    try:
        crops = data['primary_crops'] if isinstance(data['primary_crops'], str) else ','.join(data['primary_crops'])
        connection.execute('INSERT INTO farmers (id,name,location,primary_crops,farm_size,wallet_address) VALUES (?,?,?,?,?,?)', (data['id'], data['name'], data['location'], crops, data['farm_size'], data.get('wallet_address')))
        connection.commit()
        created = dict(connection.execute('SELECT * FROM farmers WHERE id=?', (data['id'],)).fetchone())
        return ok(farmer_payload(created), 201)
    except Exception:
        return fail('Could not create farmer. The id may already exist.', 409)
    finally: connection.close()

@app.get('/api/harvests')
def get_harvests():
    return ok([harvest_payload(x) for x in rows('SELECT h.*, f.name AS farmer FROM harvests h JOIN farmers f ON f.id=h.farmer_id ORDER BY h.created_at DESC')])

@app.get('/api/harvests/<harvest_id>')
def get_harvest(harvest_id):
    item = harvest_payload(row('SELECT h.*, f.name AS farmer FROM harvests h JOIN farmers f ON f.id=h.farmer_id WHERE h.id=?', (harvest_id,)))
    return ok(item) if item else fail('Harvest not found', 404)

@app.post('/api/harvests')
def create_harvest():
    data = request.get_json(silent=True) or {}
    required = ['crop', 'quantity', 'unit', 'harvest_date', 'expected_price', 'location']
    if any(data.get(key) in (None, '') for key in required): return fail('Crop, quantity, unit, harvest date, expected price, and location are required.')
    try:
        quantity = float(data['quantity']); price = float(data['expected_price'])
        if quantity <= 0 or price < 0: return fail('Quantity must be positive and price cannot be negative.')
    except (TypeError, ValueError): return fail('Quantity and expected price must be numbers.')
    connection = get_connection()
    existing = connection.execute('SELECT COUNT(*) FROM harvests').fetchone()[0]
    harvest_id = f"CR-HRV-{existing + 43:05d}"
    try:
        connection.execute('''INSERT INTO harvests (id,farmer_id,crop,quantity,unit,harvest_date,expected_price,location,description,status,proof_hash)
          VALUES (?,?,?,?,?,?,?,?,?,'REGISTERED',NULL)''', (harvest_id, data.get('farmer_id', 'farmer-01'), data['crop'], quantity, data['unit'], data['harvest_date'], price, data['location'], data.get('description', '')))
        connection.commit()
        created = dict(connection.execute('SELECT h.*, f.name AS farmer FROM harvests h JOIN farmers f ON f.id=h.farmer_id WHERE h.id=?', (harvest_id,)).fetchone())
        return ok(harvest_payload(created), 201)
    except Exception as exc:
        return fail('Could not register harvest. Check the farmer and submitted fields.', 400)
    finally: connection.close()

@app.put('/api/harvests/<harvest_id>')
def update_harvest(harvest_id):
    data = request.get_json(silent=True) or {}
    if not row('SELECT id FROM harvests WHERE id=?', (harvest_id,)): return fail('Harvest not found', 404)
    allowed = {key: data[key] for key in ['description', 'status', 'expected_price', 'quantity'] if key in data}
    if 'status' in allowed and allowed['status'] not in {'REGISTERED','PENDING','VERIFIED'}: return fail('Invalid harvest status.')
    if not allowed: return fail('No supported fields to update.')
    connection = get_connection()
    assignments = ', '.join(f'{key}=?' for key in allowed)
    connection.execute(f'UPDATE harvests SET {assignments} WHERE id=?', (*allowed.values(), harvest_id)); connection.commit(); connection.close()
    return ok(harvest_payload(row('SELECT h.*, f.name AS farmer FROM harvests h JOIN farmers f ON f.id=h.farmer_id WHERE h.id=?', (harvest_id,))))

@app.get('/api/marketplace')
def get_marketplace():
    return ok([listing_payload(x) for x in rows('SELECT * FROM marketplace_listings WHERE quantity_available > 0 ORDER BY created_at DESC')])

@app.get('/api/marketplace/<listing_id>')
def get_listing(listing_id):
    item = listing_payload(row('SELECT * FROM marketplace_listings WHERE id=?', (listing_id,)))
    return ok(item) if item else fail('Marketplace listing not found', 404)

@app.get('/api/demands')
def get_demands():
    items = rows('SELECT * FROM demands ORDER BY created_at DESC')
    for item in items:
        item['quantity_label'] = f"{item['quantity']:g} {item['unit']}"
        item['price_label'] = f"₹{item['price_min']:g}–₹{item['price_max']:g}/{item['unit']}"
    return ok(items)

@app.get('/api/demands/<demand_id>')
def get_demand(demand_id):
    item = row('SELECT * FROM demands WHERE id=?', (demand_id,))
    return ok(item) if item else fail('Demand not found', 404)

@app.get('/api/orders')
def get_orders():
    return ok([order_payload(x) for x in rows('SELECT * FROM orders ORDER BY created_at DESC')])

@app.get('/api/orders/<order_id>')
def get_order(order_id):
    item = order_payload(row('SELECT * FROM orders WHERE id=?', (order_id,)))
    return ok(item) if item else fail('Order not found', 404)

@app.post('/api/orders')
def create_order():
    data = request.get_json(silent=True) or {}
    if not data.get('listing_id') or not data.get('quantity') or not data.get('buyer_name'):
        return fail('Listing, quantity, and buyer name are required.')
    try: quantity = float(data['quantity'])
    except (TypeError, ValueError): return fail('Quantity must be a number.')
    if quantity <= 0: return fail('Quantity must be positive.')
    connection = get_connection()
    listing = connection.execute('SELECT * FROM marketplace_listings WHERE id=?', (data['listing_id'],)).fetchone()
    if not listing: connection.close(); return fail('Marketplace listing not found', 404)
    if quantity > listing['quantity_available']: connection.close(); return fail('Requested quantity is larger than available inventory.', 409)
    order_count = connection.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    order_id = f"CR-ORD-{order_count + 232:05d}"
    total = quantity * listing['price_per_unit']
    connection.execute('''INSERT INTO orders (id,harvest_id,farmer_id,buyer_name,buyer_type,quantity,unit,total_amount,status,payment_status,transaction_signature)
      VALUES (?,?,?,?,?,?,?,?,'PLACED','PENDING',NULL)''', (order_id, listing['harvest_id'], listing['farmer_id'], data['buyer_name'], data.get('buyer_type', 'RETAILER'), quantity, listing['unit'], total))
    connection.execute('UPDATE marketplace_listings SET quantity_available=quantity_available-? WHERE id=?', (quantity, data['listing_id']))
    connection.execute('INSERT INTO deliveries (id,order_id,status) VALUES (?,?,?)', (f'delivery-{order_id}', order_id, 'PENDING'))
    connection.commit()
    created = dict(connection.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()); connection.close()
    return ok(order_payload(created), 201)

@app.put('/api/orders/<order_id>/status')
def update_order_status(order_id):
    data = request.get_json(silent=True) or {}; status = data.get('status')
    allowed = {'PLACED','PROCESSING','OUT_FOR_DELIVERY','DELIVERED','COMPLETED','CANCELLED'}
    if status not in allowed: return fail('Invalid order status.')
    connection = get_connection()
    if not connection.execute('SELECT id FROM orders WHERE id=?', (order_id,)).fetchone(): connection.close(); return fail('Order not found', 404)
    connection.execute('UPDATE orders SET status=? WHERE id=?', (status, order_id)); connection.commit(); created = dict(connection.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()); connection.close()
    return ok(order_payload(created))

@app.post('/api/deliveries/<order_id>/confirm')
def confirm_delivery(order_id):
    connection = get_connection()
    if not connection.execute('SELECT id FROM orders WHERE id=?', (order_id,)).fetchone(): connection.close(); return fail('Order not found', 404)
    now = datetime.now().isoformat(timespec='seconds')
    connection.execute("UPDATE deliveries SET status='DELIVERED', confirmed_at=? WHERE order_id=?", (now, order_id))
    connection.execute("UPDATE orders SET status='DELIVERED' WHERE id=?", (order_id,))
    connection.commit(); created = dict(connection.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()); connection.close()
    return ok(order_payload(created))

@app.get('/api/farmers/<farmer_id>/passport')
def get_passport(farmer_id):
    farmer = row('SELECT * FROM farmers WHERE id=?', (farmer_id,))
    if not farmer: return fail('Farmer not found', 404)
    verified = row("SELECT COUNT(*) AS count FROM harvests WHERE farmer_id=? AND status='VERIFIED'", (farmer_id,))['count']
    completed = row("SELECT COUNT(*) AS count FROM orders WHERE farmer_id=? AND status='COMPLETED'", (farmer_id,))['count']
    total_orders = row('SELECT COUNT(*) AS count FROM orders WHERE farmer_id=?', (farmer_id,))['count']
    value = row("SELECT COALESCE(SUM(total_amount),0) AS value FROM orders WHERE farmer_id=? AND status='COMPLETED'", (farmer_id,))['value']
    fulfillment = round((row("SELECT COUNT(*) AS count FROM orders WHERE farmer_id=? AND status IN ('DELIVERED','COMPLETED')", (farmer_id,))['count'] / total_orders) * 100) if total_orders else 0
    return ok({'farmer': farmer_payload(farmer), 'verified_harvests': verified, 'completed_sales': completed, 'completed_transactions': completed, 'fulfillment_rate': f'{fulfillment}%', 'verified_trade_value': f'₹{value:,.0f}', 'evidence': {'harvest': verified > 0, 'payment': completed > 0, 'delivery': fulfillment > 0, 'onchain_reference': None}})

if __name__ == '__main__':
    init_db(); seed_db(); app.run(host='0.0.0.0', port=5000, debug=True)
