from datetime import datetime
import os
import re
import json
import urllib.request
import urllib.error
from urllib.parse import urlparse
import hashlib
from flask import Flask, jsonify, request
from flask_cors import CORS
from database import get_connection, init_db, seed_db

app = Flask(__name__)
CORS_ORIGINS = [origin.strip() for origin in os.getenv('CROP_CRED_CORS_ORIGINS', '*').split(',') if origin.strip()]
CORS(app, resources={r'/api/*': {'origins': CORS_ORIGINS}})
DEVNET_RPC = os.getenv('SOLANA_DEVNET_RPC_URL', 'https://api.devnet.solana.com')
_rpc_host = (urlparse(DEVNET_RPC).hostname or '').lower()
_is_devnet_host = _rpc_host == 'devnet.solana.com' or _rpc_host.endswith('.devnet.solana.com')
if not DEVNET_RPC.lower().startswith(('https://', 'http://')) or not _is_devnet_host or 'mainnet' in _rpc_host:
    raise RuntimeError('CropCred only supports a Solana Devnet RPC endpoint.')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '').strip()
OPENROUTER_FREE_MODEL = os.getenv('OPENROUTER_FREE_MODEL', 'meta-llama/llama-3.1-8b-instruct:free')
OPENROUTER_BEST_MODEL = os.getenv('OPENROUTER_BEST_MODEL', 'anthropic/claude-3.5-sonnet')
OPENROUTER_BASE_URL = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1/chat/completions')
DEMO_SOL_AMOUNT = 0.001


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
    item = dict(item)
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


def crop_batch_payload(item):
    if not item: return None
    item = dict(item)
    item['price_range_label'] = f"₹{item['expected_price_min']:g}–₹{item['expected_price_max']:g}/{item['unit']}"
    item['harvest_date_label'] = item['harvest_date']
    item['availability_label'] = item['availability_status'].replace('_', ' ').title()
    item['quality_label'] = item['quality_status'].replace('_', ' ').title()
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


def auction_payload(item):
    if not item: return None
    item = dict(item)
    item['price_range_label'] = f"₹{item['price_min']:g}–₹{item['price_max']:g}/{item['unit']}"
    item['deadline_label'] = item.get('deadline', '')
    return item


def create_order_record(connection, farmer_id, buyer_name, buyer_type, harvest_id, quantity, unit, total_amount):
    order_count = connection.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    order_id = f"CR-ORD-{order_count + 232:05d}"
    connection.execute('''INSERT INTO orders (id,harvest_id,farmer_id,buyer_name,buyer_type,quantity,unit,total_amount,status,payment_status,transaction_signature)
      VALUES (?,?,?,?,?,?,?,?,'PENDING_PAYMENT','PENDING',NULL)''', (order_id, harvest_id, farmer_id, buyer_name, buyer_type, quantity, unit, total_amount))
    connection.execute('INSERT INTO deliveries (id,order_id,status) VALUES (?,?,?)', (f'delivery-{order_id}', order_id, 'PENDING'))
    created = dict(connection.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone())
    return created


def rpc_call(method, params):
    payload = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    request = urllib.request.Request(DEVNET_RPC, data=payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=12) as response:
        body = json.loads(response.read().decode())
    if body.get('error'):
        raise ValueError('Devnet RPC returned an error')
    return body.get('result')


def valid_solana_address(value):
    return bool(value and re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,44}', str(value)))


def explorer_url(signature):
    return f'https://explorer.solana.com/tx/{signature}?cluster=devnet'


def mark_payment_failed(connection, payment_id):
    connection.execute("UPDATE payments SET status='FAILED' WHERE id=? AND status='PROCESSING'", (payment_id,))
    connection.commit()


def crop_batch_credential_payload(item):
    if not item: return None
    item = dict(item)
    try:
        item['metadata'] = json.loads(item.get('metadata_json') or '{}') if item.get('metadata_json') else {}
    except (TypeError, ValueError):
        item['metadata'] = {'raw': item.get('metadata_json')}
    item['status_label'] = item.get('status', 'PENDING').replace('_', ' ').title()
    item['timestamp'] = item.get('verified_at') or item.get('created_at')
    item['network_label'] = (item.get('network') or 'devnet').upper()
    item['transaction_url'] = explorer_url(item['transaction_signature']) if item.get('transaction_signature') else None
    return item


def build_crop_batch_credential(batch):
    evidence = {
        'batch_id': batch['id'],
        'crop_id': batch['harvest_id'],
        'farmer_id': batch['farmer_id'],
        'crop_type': batch['crop_name'],
        'quantity': float(batch['quantity']),
        'unit': batch['unit'],
        'harvest_date': batch['harvest_date'],
        'farm_reference': batch['farmer_id'],
        'evidence_fingerprint': batch['fingerprint'],
    }
    metadata = {
        'network': 'devnet',
        'crop_type': batch['crop_name'],
        'quantity': float(batch['quantity']),
        'unit': batch['unit'],
        'farmer_reference': batch['farmer_id'],
        'harvest_id': batch['harvest_id'],
        'harvest_date': batch['harvest_date'],
        'farmer_identity_reference': batch['farmer_id'],
        'status': 'PENDING',
        'verification': 'Awaiting Solana Devnet confirmation',
    }
    evidence_hash = hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    metadata_hash = hashlib.sha256(json.dumps(metadata, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    ref_seed = f"{batch['id']}:{batch['farmer_id']}:{batch['crop_name']}"
    credential_reference = f"CR-DC-{batch['id']}-{hashlib.sha256(ref_seed.encode()).hexdigest()[:10].upper()}"
    return credential_reference, evidence_hash, metadata_hash, metadata


def ensure_crop_batch_credential(connection, batch_id, wallet_address=None, transaction_signature=None, network='devnet', status=None):
    batch = connection.execute('''SELECT b.*, f.wallet_address AS farmer_wallet, h.status AS harvest_status, h.location AS harvest_location FROM crop_batches b JOIN farmers f ON f.id=b.farmer_id JOIN harvests h ON h.id=b.harvest_id WHERE b.id=?''', (batch_id,)).fetchone()
    if not batch:
        return None
    credential_reference, evidence_hash, metadata_hash, metadata = build_crop_batch_credential(batch)
    if status is None:
        status = 'VERIFIED' if batch['harvest_status'] == 'VERIFIED' else 'PENDING'
    if transaction_signature:
        status = 'VERIFIED'
    network = (network or 'devnet').lower()
    existing = connection.execute('SELECT * FROM crop_batch_credentials WHERE batch_id=?', (batch_id,)).fetchone()
    now = datetime.now().isoformat(timespec='seconds')
    if existing:
        connection.execute('''UPDATE crop_batch_credentials SET crop_id=?, farmer_identity_ref=?, crop_type=?, quantity=?, unit=?, harvest_id=?, harvest_date=?, harvest_location=?, evidence_hash=?, metadata_hash=?, status=?, network=?, wallet_address=?, transaction_signature=?, metadata_json=?, updated_at=? WHERE batch_id=?''', (
            batch['harvest_id'],
            batch['farmer_id'],
            batch['crop_name'],
            float(batch['quantity']),
            batch['unit'],
            batch['harvest_id'],
            batch['harvest_date'],
            batch['harvest_location'],
            evidence_hash,
            metadata_hash,
            status,
            network,
            wallet_address or existing['wallet_address'] or batch['farmer_wallet'],
            transaction_signature or existing['transaction_signature'],
            json.dumps(metadata, sort_keys=True),
            now,
            batch_id,
        ))
        if transaction_signature and not existing['verified_at']:
            connection.execute('UPDATE crop_batch_credentials SET verified_at=? WHERE batch_id=?', (now, batch_id))
        if not transaction_signature and status == 'VERIFIED':
            connection.execute('UPDATE crop_batch_credentials SET verified_at=? WHERE batch_id=?', (now, batch_id))
    else:
        connection.execute('''INSERT INTO crop_batch_credentials (id,batch_id,crop_id,farmer_id,farmer_identity_ref,crop_type,quantity,unit,harvest_id,harvest_date,harvest_location,evidence_hash,metadata_hash,status,network,wallet_address,transaction_signature,verified_at,metadata_json,created_at,updated_at)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
            credential_reference,
            batch_id,
            batch['harvest_id'],
            batch['farmer_id'],
            batch['farmer_id'],
            batch['crop_name'],
            float(batch['quantity']),
            batch['unit'],
            batch['harvest_id'],
            batch['harvest_date'],
            batch['harvest_location'],
            evidence_hash,
            metadata_hash,
            status,
            network,
            wallet_address or batch['farmer_wallet'],
            transaction_signature,
            now if transaction_signature else None,
            json.dumps(metadata, sort_keys=True),
            now,
            now,
        ))
    item = connection.execute('SELECT * FROM crop_batch_credentials WHERE batch_id=?', (batch_id,)).fetchone()
    return crop_batch_credential_payload(item)


def credential_snapshot(connection, farmer_id):
    farmer = connection.execute('SELECT * FROM farmers WHERE id=?', (farmer_id,)).fetchone()
    if not farmer: return None
    harvests = connection.execute("SELECT COUNT(*) AS count FROM harvests WHERE farmer_id=? AND status='VERIFIED'", (farmer_id,)).fetchone()['count']
    sales = connection.execute("SELECT COUNT(*) AS count FROM orders WHERE farmer_id=? AND payment_status='PAID'", (farmer_id,)).fetchone()['count']
    payments_count = connection.execute("SELECT COUNT(*) AS count FROM payments p JOIN orders o ON o.id=p.order_id WHERE o.farmer_id=? AND p.status='VERIFIED'", (farmer_id,)).fetchone()['count']
    deliveries = connection.execute("SELECT COUNT(*) AS count FROM deliveries d JOIN orders o ON o.id=d.order_id WHERE o.farmer_id=? AND d.status='DELIVERED'", (farmer_id,)).fetchone()['count']
    trade_value = connection.execute("SELECT COALESCE(SUM(total_amount),0) AS value FROM orders WHERE farmer_id=? AND payment_status='PAID'", (farmer_id,)).fetchone()['value']
    total_orders = connection.execute('SELECT COUNT(*) AS count FROM orders WHERE farmer_id=?', (farmer_id,)).fetchone()['count']
    batch_rows = connection.execute('SELECT id, fingerprint FROM crop_batches WHERE farmer_id=? ORDER BY id', (farmer_id,)).fetchall()
    batch_count = len(batch_rows)
    canonical = {'farmer_id': farmer_id, 'harvests': harvests, 'sales': sales, 'payments': payments_count, 'deliveries': deliveries, 'trade_value': trade_value, 'crop_batches': [dict(item) for item in batch_rows]}
    fingerprint = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    credential = connection.execute('SELECT * FROM economic_credentials WHERE farmer_id=?', (farmer_id,)).fetchone()
    now = datetime.now().isoformat(timespec='seconds')
    if credential:
        version = credential['version'] if credential['fingerprint'] == fingerprint else credential['version'] + 1
        connection.execute('''UPDATE economic_credentials SET version=?, status=?, fingerprint=?, credential_hash=?, evidence_count=?, verified_transaction_count=?, updated_at=? WHERE farmer_id=?''', (version, 'VERIFIED' if payments_count else 'PENDING_VERIFICATION', fingerprint, fingerprint, harvests + sales + payments_count + deliveries + batch_count, payments_count, now, farmer_id))
    else:
        credential_id = f'CR-CRED-{farmer_id[-2:].upper()}'
        connection.execute('''INSERT INTO economic_credentials (id,farmer_id,credential_id,credential_type,evidence_count,verified_transaction_count,version,status,fingerprint,credential_hash,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)''', (f'credential-{farmer_id}', farmer_id, credential_id, 'ECONOMIC_CREDENTIAL', harvests + sales + payments_count + deliveries + batch_count, payments_count, 1, 'VERIFIED' if payments_count else 'PENDING_VERIFICATION', fingerprint, fingerprint, now))
    credential_row = connection.execute('SELECT id FROM economic_credentials WHERE farmer_id=?', (farmer_id,)).fetchone()
    evidence_rows = []
    for item in connection.execute("SELECT id FROM harvests WHERE farmer_id=? AND status='VERIFIED'", (farmer_id,)).fetchall(): evidence_rows.append(('HARVEST_REGISTERED', 'harvest', item['id'], 1))
    for item in connection.execute('SELECT id FROM orders WHERE farmer_id=?', (farmer_id,)).fetchall(): evidence_rows.append(('ORDER_CREATED', 'order', item['id'], 1))
    for item in connection.execute("SELECT p.id FROM payments p JOIN orders o ON o.id=p.order_id WHERE o.farmer_id=? AND p.status='VERIFIED'", (farmer_id,)).fetchall(): evidence_rows.append(('PAYMENT_VERIFIED', 'payment', item['id'], 1))
    for item in connection.execute("SELECT d.id FROM deliveries d JOIN orders o ON o.id=d.order_id WHERE o.farmer_id=? AND d.status='DELIVERED'", (farmer_id,)).fetchall(): evidence_rows.append(('DELIVERY_CONFIRMED', 'delivery', item['id'], 1))
    for item in batch_rows: evidence_rows.append(('CROP_BATCH_CREATED', 'crop_batch', item['id'], 1))
    for item in connection.execute("SELECT id FROM crop_auctions WHERE status='AWARDED' AND id IN (SELECT auction_id FROM auction_offers WHERE farmer_id=? AND status='ACCEPTED')", (farmer_id,)).fetchall(): evidence_rows.append(('AUCTION_AWARDED', 'auction', item['id'], 1))
    for item in connection.execute("SELECT id FROM auction_offers WHERE farmer_id=? AND status='SUBMITTED'", (farmer_id,)).fetchall(): evidence_rows.append(('AUCTION_OFFER_SUBMITTED', 'auction_offer', item['id'], 1))
    for item in connection.execute("SELECT id FROM crop_auctions WHERE crop_batch_id IN (SELECT id FROM crop_batches WHERE farmer_id=?)", (farmer_id,)).fetchall(): evidence_rows.append(('AUCTION_CREATED', 'auction', item['id'], 1))
    for evidence_type, reference_type, reference_id, verified in evidence_rows:
        connection.execute('INSERT OR IGNORE INTO credential_evidence (id,credential_id,evidence_type,reference_type,reference_id,verified) VALUES (?,?,?,?,?,?)', (f'{evidence_type.lower()}-{reference_id}', credential_row['id'], evidence_type, reference_type, reference_id, verified))
    connection.commit()
    return {'farmer': farmer_payload(farmer), 'verified_harvests': harvests, 'completed_sales': sales, 'verified_payments': payments_count, 'verified_deliveries': deliveries, 'verified_trade_value': trade_value, 'crop_batches': batch_count, 'total_orders': total_orders, 'fulfillment_rate': round(deliveries / total_orders * 100) if total_orders else None}


def credential_evidence(connection, farmer_id):
    rows = connection.execute('''SELECT o.id AS order_id, o.created_at, o.quantity, o.unit, o.total_amount, o.buyer_name, o.payment_status, o.transaction_signature, h.id AS harvest_id, h.crop, h.harvest_date, d.status AS delivery_status, p.status AS blockchain_status, p.payer_wallet, p.recipient_wallet, p.amount_sol, p.verified_at FROM orders o JOIN harvests h ON h.id=o.harvest_id LEFT JOIN deliveries d ON d.order_id=o.id LEFT JOIN payments p ON p.order_id=o.id AND p.status='VERIFIED' WHERE o.farmer_id=? ORDER BY o.created_at DESC''', (farmer_id,)).fetchall()
    result = [dict(item) for item in rows]
    batch_rows = connection.execute('''SELECT b.id AS batch_id, b.created_at, b.harvest_id, b.crop_name AS crop, b.quantity, b.unit, b.expected_price_min, b.expected_price_max, b.availability_status, b.quality_status, b.fingerprint, 'CROP_BATCH_CREATED' AS evidence_type FROM crop_batches b WHERE b.farmer_id=? ORDER BY b.created_at DESC''', (farmer_id,)).fetchall()
    return result + [dict(item) for item in batch_rows]

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

@app.put('/api/farmers/<farmer_id>/wallet')
def update_farmer_wallet(farmer_id):
    data = request.get_json(silent=True) or {}
    if 'wallet_address' not in data:
        return fail('wallet_address is required.')
    wallet_address = str(data.get('wallet_address') or '').strip()
    if wallet_address and not re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{32,44}', wallet_address):
        return fail('Enter a valid Solana public wallet address.')
    connection = get_connection()
    if not connection.execute('SELECT id FROM farmers WHERE id=?', (farmer_id,)).fetchone():
        connection.close(); return fail('Farmer not found', 404)
    connection.execute('UPDATE farmers SET wallet_address=? WHERE id=?', (wallet_address or None, farmer_id))
    connection.commit(); connection.close()
    return ok({'wallet_address': wallet_address})

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


def crop_batch_query(connection, where='1=1', params=()):
    return [crop_batch_payload(item) for item in connection.execute(f'''SELECT b.*, f.name AS farmer, h.id AS linked_harvest_id, h.crop AS harvest_crop, h.status AS harvest_status
      FROM crop_batches b JOIN farmers f ON f.id=b.farmer_id JOIN harvests h ON h.id=b.harvest_id WHERE {where} ORDER BY b.created_at DESC''', params).fetchall()]


@app.get('/api/crop-batches')
def get_crop_batches():
    connection = get_connection(); items = crop_batch_query(connection); connection.close(); return ok(items)


@app.get('/api/crop-batches/<batch_id>')
def get_crop_batch(batch_id):
    connection = get_connection(); items = crop_batch_query(connection, 'b.id=?', (batch_id,)); connection.close()
    return ok(items[0]) if items else fail('Crop batch not found', 404)


@app.get('/api/crop-batches/<batch_id>/credential')
def get_crop_batch_credential(batch_id):
    connection = get_connection()
    credential = connection.execute('SELECT * FROM crop_batch_credentials WHERE batch_id=?', (batch_id,)).fetchone()
    if not credential:
        if not connection.execute('SELECT id FROM crop_batches WHERE id=?', (batch_id,)).fetchone():
            connection.close(); return fail('Crop batch not found', 404)
        credential = ensure_crop_batch_credential(connection, batch_id)
    connection.close()
    return ok(crop_batch_credential_payload(credential)) if credential else fail('Crop batch credential is not available yet.', 404)


@app.post('/api/crop-batches/<batch_id>/credential')
def upsert_crop_batch_credential(batch_id):
    data = request.get_json(silent=True) or {}
    connection = get_connection()
    if not connection.execute('SELECT id FROM crop_batches WHERE id=?', (batch_id,)).fetchone():
        connection.close(); return fail('Crop batch not found', 404)
    wallet_address = str(data.get('wallet_address') or '').strip() or None
    transaction_signature = str(data.get('transaction_signature') or '').strip() or None
    network = str(data.get('network') or 'devnet').strip().lower()
    if network != 'devnet':
        connection.close(); return fail('CropCred only supports Solana Devnet.', 400)
    if transaction_signature and wallet_address and valid_solana_address(wallet_address):
        try:
            tx = rpc_call('getTransaction', [transaction_signature, {'encoding': 'jsonParsed', 'commitment': 'confirmed', 'maxSupportedTransactionVersion': 0}])
            if not tx or tx.get('meta', {}).get('err') is not None:
                raise ValueError()
            status = 'VERIFIED'
        except Exception:
            status = 'UNVERIFIED'
    else:
        status = 'PENDING'
    credential = ensure_crop_batch_credential(connection, batch_id, wallet_address=wallet_address, transaction_signature=transaction_signature, network=network, status=status)
    connection.commit(); connection.close(); return ok(credential)


@app.post('/api/crop-batches')
def create_crop_batch():
    data = request.get_json(silent=True) or {}
    harvest_id = str(data.get('harvest_id', '')).strip(); variety = str(data.get('variety', '')).strip()
    if not harvest_id or not variety: return fail('A linked harvest and variety are required.')
    connection = get_connection()
    harvest = connection.execute('SELECT h.*, f.name AS farmer FROM harvests h JOIN farmers f ON f.id=h.farmer_id WHERE h.id=?', (harvest_id,)).fetchone()
    if not harvest: connection.close(); return fail('Linked harvest not found', 404)
    existing = connection.execute('SELECT id FROM crop_batches WHERE harvest_id=?', (harvest_id,)).fetchone()
    if existing:
        item = crop_batch_query(connection, 'b.id=?', (existing['id'],))[0]; connection.close(); return ok(item)
    try:
        quantity = float(data.get('quantity', harvest['quantity'])); price_min = float(data.get('expected_price_min', harvest['expected_price'])); price_max = float(data.get('expected_price_max', price_min))
    except (TypeError, ValueError):
        connection.close(); return fail('Quantity and expected price range must be numbers.')
    if quantity <= 0 or quantity > harvest['quantity'] or price_min < 0 or price_max < price_min: connection.close(); return fail('Use a positive quantity within the harvest and a valid price range.')
    availability = str(data.get('availability_status', 'AVAILABLE')).upper(); quality = str(data.get('quality_status', 'PENDING')).upper()
    if availability not in {'AVAILABLE', 'RESERVED', 'SOLD', 'UNAVAILABLE'} or quality not in {'PENDING', 'SELF_DECLARED', 'CERTIFICATION_PENDING', 'CERTIFIED'}:
        connection.close(); return fail('Invalid availability or quality status.')
    canonical = {'harvest_id': harvest_id, 'farmer_id': harvest['farmer_id'], 'crop_name': harvest['crop'], 'variety': variety, 'quantity': quantity, 'unit': data.get('unit', harvest['unit']), 'harvest_date': harvest['harvest_date'], 'expected_price_min': price_min, 'expected_price_max': price_max, 'availability_status': availability, 'quality_status': quality}
    fingerprint = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    next_number = 1042
    while connection.execute('SELECT 1 FROM crop_batches WHERE id=?', (f'CRP-{next_number}',)).fetchone(): next_number += 1
    batch_id = f'CRP-{next_number}'
    try:
        connection.execute('''INSERT INTO crop_batches (id,farmer_id,harvest_id,crop_name,variety,quantity,unit,harvest_date,expected_price_min,expected_price_max,availability_status,quality_status,fingerprint)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''', (batch_id, harvest['farmer_id'], harvest_id, harvest['crop'], variety, quantity, canonical['unit'], harvest['harvest_date'], price_min, price_max, availability, quality, fingerprint))
        ensure_crop_batch_credential(connection, batch_id, wallet_address=harvest.get('wallet_address') or None)
        credential_snapshot(connection, harvest['farmer_id'])
        item = crop_batch_query(connection, 'b.id=?', (batch_id,))[0]
        connection.commit(); connection.close(); return ok(item, 201)
    except Exception:
        connection.rollback(); connection.close(); return fail('Could not create the crop batch.', 400)


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
    items = rows('SELECT d.*, COUNT(r.id) AS response_count FROM demands d LEFT JOIN demand_responses r ON r.demand_id=d.id GROUP BY d.id ORDER BY d.created_at DESC')
    for item in items:
        item['quantity_label'] = f"{item['quantity']:g} {item['unit']}"
        item['price_label'] = f"₹{item['price_min']:g}–₹{item['price_max']:g}/{item['unit']}"
        item['buyer_verified'] = bool(row('SELECT 1 AS ok FROM buyer_profiles WHERE business_name=? AND verification_status=\'VERIFIED\'', (item['buyer_name'],)))
    return ok(items)

@app.post('/api/demands')
def create_demand():
    data = request.get_json(silent=True) or {}
    required = ['buyer_name', 'buyer_type', 'crop', 'quantity', 'unit', 'required_date', 'frequency', 'min_price', 'max_price', 'location']
    if any(data.get(key) in (None, '') for key in required): return fail('Product, quantity, date, frequency, price range, and location are required.')
    try: quantity, min_price, max_price = float(data['quantity']), float(data['min_price']), float(data['max_price'])
    except (TypeError, ValueError): return fail('Quantity and price values must be numbers.')
    if quantity <= 0 or min_price < 0 or max_price < min_price: return fail('Use a positive quantity and a valid non-negative price range.')
    try: datetime.fromisoformat(str(data['required_date']))
    except ValueError: return fail('Required date must be a valid ISO date.')
    connection = get_connection(); demand_id = f"DEM-{connection.execute('SELECT COUNT(*) FROM demands').fetchone()[0] + 1001}"
    connection.execute('''INSERT INTO demands (id,buyer_name,buyer_type,crop,quantity,unit,price_min,price_max,location,frequency,deadline,requirements,status,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (demand_id, data['buyer_name'], data['buyer_type'], str(data['crop']).strip(), quantity, data['unit'], min_price, max_price, data['location'], data['frequency'], str(data['required_date']), data.get('requirements','').strip(), 'OPEN', datetime.now().isoformat(timespec='seconds')))
    connection.execute('INSERT OR IGNORE INTO buyer_profiles (id,business_name,buyer_type,verification_status) VALUES (?,?,?,?)', (f'buyer-{demand_id}', data['buyer_name'], data['buyer_type'], 'VERIFIED'))
    connection.commit(); item = dict(connection.execute('SELECT * FROM demands WHERE id=?', (demand_id,)).fetchone()); connection.close(); return ok(item, 201)

@app.get('/api/demands/<demand_id>')
def get_demand(demand_id):
    item = row('SELECT d.*, COUNT(r.id) AS response_count FROM demands d LEFT JOIN demand_responses r ON r.demand_id=d.id WHERE d.id=? GROUP BY d.id', (demand_id,))
    return ok(item) if item else fail('Demand not found', 404)

@app.post('/api/demands/<demand_id>/respond')
def respond_to_demand(demand_id):
    data = request.get_json(silent=True) or {}
    try: quantity = float(data.get('quantity_offered')); expected_price = float(data.get('expected_price'))
    except (TypeError, ValueError): return fail('Offered quantity and expected price are required.')
    connection = get_connection(); demand = connection.execute('SELECT * FROM demands WHERE id=?', (demand_id,)).fetchone()
    if not demand: connection.close(); return fail('Demand not found', 404)
    if demand['status'] != 'OPEN': connection.close(); return fail('Only OPEN demands accept responses.', 409)
    farmer_id = data.get('farmer_id', 'farmer-01')
    if not connection.execute('SELECT id FROM farmers WHERE id=?', (farmer_id,)).fetchone(): connection.close(); return fail('Farmer not found', 404)
    if quantity <= 0 or quantity > demand['quantity'] or expected_price < demand['price_min'] or expected_price > demand['price_max']: connection.close(); return fail('Response quantity or price is outside the demand requirements.')
    response_id = f"RESP-{connection.execute('SELECT COUNT(*) FROM demand_responses').fetchone()[0] + 1001}"
    connection.execute('''INSERT INTO demand_responses (id,demand_id,farmer_id,quantity_offered,expected_price,available_date,status) VALUES (?,?,?,?,?,?,?)''', (response_id, demand_id, farmer_id, quantity, expected_price, data.get('available_date', demand['deadline']), 'SUBMITTED'))
    connection.execute("UPDATE demands SET status='RESPONSES_RECEIVED', updated_at=? WHERE id=? AND status='OPEN'", (datetime.now().isoformat(timespec='seconds'), demand_id)); connection.commit(); response = connection.execute('''SELECT r.*, f.name, f.location FROM demand_responses r JOIN farmers f ON f.id=r.farmer_id WHERE r.id=?''', (response_id,)).fetchone(); connection.close(); return ok(dict(response), 201)

@app.get('/api/demands/<demand_id>/responses')
def get_demand_responses(demand_id):
    connection = get_connection(); demand = connection.execute('SELECT * FROM demands WHERE id=?', (demand_id,)).fetchone()
    if not demand: connection.close(); return fail('Demand not found', 404)
    responses = [dict(item) for item in connection.execute('''SELECT r.*, f.name, f.location, f.wallet_address, (SELECT COUNT(*) FROM harvests h WHERE h.farmer_id=f.id AND h.status='VERIFIED') AS verified_harvests, (SELECT COUNT(*) FROM orders o WHERE o.farmer_id=f.id AND o.payment_status='PAID') AS completed_sales, (SELECT COUNT(*) FROM payments p JOIN orders o ON o.id=p.order_id WHERE o.farmer_id=f.id AND p.status='VERIFIED') AS verified_payments FROM demand_responses r JOIN farmers f ON f.id=r.farmer_id WHERE r.demand_id=? ORDER BY r.created_at DESC''', (demand_id,)).fetchall()]; connection.close()
    for item in responses:
        item['match_reasons'] = ['Quantity available', 'Date compatible', 'Price within buyer range', 'Relevant verified harvest']
        item['match_fit'] = min(100, 60 + (20 if item['quantity_offered'] >= demand['quantity'] * .5 else 10) + (10 if demand['price_min'] <= item['expected_price'] <= demand['price_max'] else 0) + (10 if item['verified_harvests'] else 0))
    return ok(responses)

@app.get('/api/auctions')
def get_auctions():
    connection = get_connection()
    auctions = [dict(item) for item in connection.execute('''SELECT a.*, COUNT(o.id) AS offer_count FROM crop_auctions a LEFT JOIN auction_offers o ON o.auction_id=a.id GROUP BY a.id ORDER BY a.created_at DESC''').fetchall()]
    connection.close(); return ok([auction_payload(item) for item in auctions])

@app.post('/api/auctions')
def create_auction():
    data = request.get_json(silent=True) or {}
    required = ['buyer_name','buyer_type','crop','quantity','unit','price_min','price_max','deadline','delivery_location']
    if any(data.get(key) in (None, '') for key in required): return fail('Buyer, crop, quantity, unit, pricing, deadline, and delivery location are required.')
    try:
        quantity = float(data['quantity']); price_min = float(data['price_min']); price_max = float(data['price_max'])
    except (TypeError, ValueError): return fail('Quantity and pricing values must be numbers.')
    if quantity <= 0 or price_min < 0 or price_max < price_min: return fail('Use a positive quantity and a valid price range.')
    connection = get_connection(); auction_id = f"AUC-{connection.execute('SELECT COUNT(*) FROM crop_auctions').fetchone()[0] + 1001}"
    crop_batch_id = data.get('crop_batch_id') or None
    if crop_batch_id and not connection.execute('SELECT id FROM crop_batches WHERE id=?', (crop_batch_id,)).fetchone(): connection.close(); return fail('Selected crop batch was not found.', 404)
    connection.execute('''INSERT INTO crop_auctions (id,buyer_name,buyer_type,crop,crop_batch_id,quantity,unit,price_min,price_max,deadline,delivery_location,quality_requirements,evidence_requirements,status,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (auction_id, str(data['buyer_name']).strip(), str(data['buyer_type']).upper(), str(data['crop']).strip(), crop_batch_id, quantity, str(data['unit']).strip() or 'kg', price_min, price_max, str(data['deadline']).strip(), str(data['delivery_location']).strip(), data.get('quality_requirements') or '', data.get('evidence_requirements') or '', 'OPEN', datetime.now().isoformat(timespec='seconds')))
    connection.execute('INSERT OR IGNORE INTO buyer_profiles (id,business_name,buyer_type,verification_status) VALUES (?,?,?,?)', (f'buyer-{auction_id}', str(data['buyer_name']).strip(), str(data['buyer_type']).upper(), 'VERIFIED'))
    connection.commit(); item = dict(connection.execute('SELECT * FROM crop_auctions WHERE id=?', (auction_id,)).fetchone()); connection.close(); return ok(auction_payload(item), 201)

@app.get('/api/auctions/<auction_id>')
def get_auction(auction_id):
    item = row('SELECT * FROM crop_auctions WHERE id=?', (auction_id,))
    return ok(auction_payload(item)) if item else fail('Auction not found', 404)

@app.post('/api/auctions/<auction_id>/offers')
def create_auction_offer(auction_id):
    data = request.get_json(silent=True) or {}
    try: quantity = float(data.get('quantity')); offered_price = float(data.get('offered_price'))
    except (TypeError, ValueError): return fail('Offered quantity and price are required.')
    if quantity <= 0 or offered_price < 0: return fail('Offer quantity and price must be positive values.')
    connection = get_connection(); auction = connection.execute('SELECT * FROM crop_auctions WHERE id=?', (auction_id,)).fetchone()
    if not auction: connection.close(); return fail('Auction not found', 404)
    if auction['status'] not in ('OPEN','OFFER_RECEIVED'):
        connection.close(); return fail('This auction is no longer accepting offers.', 409)
    farmer_id = str(data.get('farmer_id') or '').strip() or 'farmer-01'
    if not connection.execute('SELECT id FROM farmers WHERE id=?', (farmer_id,)).fetchone(): connection.close(); return fail('Farmer not found', 404)
    crop_batch_id = data.get('crop_batch_id') or None
    if crop_batch_id and not connection.execute('SELECT id FROM crop_batches WHERE id=?', (crop_batch_id,)).fetchone(): connection.close(); return fail('This crop batch was not found.', 404)
    offer_id = f"AOF-{connection.execute('SELECT COUNT(*) FROM auction_offers').fetchone()[0] + 1001}"
    connection.execute('''INSERT INTO auction_offers (id,auction_id,farmer_id,crop_batch_id,quantity,offered_price,delivery_estimate,message,status,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)''', (offer_id, auction_id, farmer_id, crop_batch_id, quantity, offered_price, str(data.get('delivery_estimate') or 'TBD').strip() or 'TBD', (data.get('message') or '').strip(), 'SUBMITTED', datetime.now().isoformat(timespec='seconds')))
    connection.execute("UPDATE crop_auctions SET status='OFFER_RECEIVED', updated_at=? WHERE id=? AND status IN ('OPEN','OFFER_RECEIVED')", (datetime.now().isoformat(timespec='seconds'), auction_id));
    connection.commit(); item = dict(connection.execute('SELECT * FROM auction_offers WHERE id=?', (offer_id,)).fetchone()); credential_snapshot(connection, farmer_id); connection.close(); return ok(item, 201)

@app.get('/api/auctions/<auction_id>/offers')
def get_auction_offers(auction_id):
    connection = get_connection(); auction = connection.execute('SELECT * FROM crop_auctions WHERE id=?', (auction_id,)).fetchone();
    if not auction: connection.close(); return fail('Auction not found', 404)
    offers = [dict(item) for item in connection.execute('''SELECT ao.*, f.name AS farmer_name, f.location AS farmer_location, cb.crop_name, cb.variety, cb.quality_status FROM auction_offers ao LEFT JOIN farmers f ON f.id=ao.farmer_id LEFT JOIN crop_batches cb ON cb.id=ao.crop_batch_id WHERE ao.auction_id=? ORDER BY ao.created_at DESC''', (auction_id,)).fetchall()]
    connection.close(); return ok(offers)

@app.post('/api/auctions/<auction_id>/award')
def award_auction_offer(auction_id):
    data = request.get_json(silent=True) or {}
    offer_id = str(data.get('offer_id') or '').strip();
    if not offer_id: return fail('An offer_id is required to award the auction.')
    connection = get_connection()
    try:
        auction = connection.execute('SELECT * FROM crop_auctions WHERE id=?', (auction_id,)).fetchone(); offer = connection.execute('SELECT * FROM auction_offers WHERE id=? AND auction_id=?', (offer_id, auction_id)).fetchone()
        if not auction or not offer: return fail('Auction or offer not found', 404)
        if auction['status'] not in ('OPEN','OFFER_RECEIVED','CLOSED'): return fail('This auction is not eligible to award a farmer.', 409)
        if offer['status'] != 'SUBMITTED': return fail('This offer is no longer available to accept.', 409)
        crop_batch = connection.execute('SELECT * FROM crop_batches WHERE id=?', (offer['crop_batch_id'],)).fetchone() if offer['crop_batch_id'] else None
        if crop_batch and crop_batch['farmer_id'] == offer['farmer_id']:
            harvest = connection.execute('SELECT * FROM harvests WHERE id=?', (crop_batch['harvest_id'],)).fetchone()
        else:
            harvest = connection.execute("SELECT * FROM harvests WHERE farmer_id=? AND crop LIKE ? AND status='VERIFIED' AND quantity>=? ORDER BY harvest_date DESC LIMIT 1", (offer['farmer_id'], auction['crop'], offer['quantity'])).fetchone()
        if not harvest: return fail('This farmer has no valid verified harvest for the awarded auction quantity.', 409)
        total_amount = float(offer['quantity']) * float(offer['offered_price'])
        order = create_order_record(connection, offer['farmer_id'], auction['buyer_name'], auction['buyer_type'], harvest['id'], offer['quantity'], auction['unit'], total_amount)
        connection.execute("UPDATE auction_offers SET status='ACCEPTED', updated_at=? WHERE auction_id=? AND id=?", (datetime.now().isoformat(timespec='seconds'), auction_id, offer_id))
        connection.execute("UPDATE auction_offers SET status='REJECTED', updated_at=? WHERE auction_id=? AND id<>? AND status IN ('SUBMITTED','WITHDRAWN')", (datetime.now().isoformat(timespec='seconds'), auction_id, offer_id))
        connection.execute("UPDATE crop_auctions SET status='AWARDED', updated_at=? WHERE id=?", (datetime.now().isoformat(timespec='seconds'), auction_id))
        connection.commit(); credential_snapshot(connection, offer['farmer_id']); auction_row = dict(connection.execute('SELECT * FROM crop_auctions WHERE id=?', (auction_id,)).fetchone()); offer_row = dict(connection.execute('SELECT * FROM auction_offers WHERE id=?', (offer_id,)).fetchone());
        return ok({'auction': auction_payload(auction_row), 'offer': offer_row, 'order': order})
    finally:
        connection.close()

@app.post('/api/demands/<demand_id>/accept/<response_id>')
def accept_demand_response(demand_id, response_id):
    connection = get_connection(); demand = connection.execute('SELECT * FROM demands WHERE id=?', (demand_id,)).fetchone(); response = connection.execute('SELECT * FROM demand_responses WHERE id=? AND demand_id=?', (response_id, demand_id)).fetchone()
    if not demand or not response: connection.close(); return fail('Demand or response not found', 404)
    if demand['status'] not in ('OPEN','RESPONSES_RECEIVED'): connection.close(); return fail('This demand is no longer accepting a match.', 409)
    if response['status'] not in ('SUBMITTED','SHORTLISTED'): connection.close(); return fail('This response cannot be accepted.', 409)
    harvest = connection.execute("SELECT * FROM harvests WHERE farmer_id=? AND crop LIKE ? AND status='VERIFIED' AND quantity>=? ORDER BY harvest_date DESC LIMIT 1", (response['farmer_id'], demand['crop'], response['quantity_offered'])).fetchone()
    if not harvest: connection.close(); return fail('Farmer has no matching verified harvest with sufficient quantity.', 409)
    order_id = f"CR-ORD-{connection.execute('SELECT COUNT(*) FROM orders').fetchone()[0] + 232:05d}"; total = response['quantity_offered'] * response['expected_price']
    connection.execute("UPDATE demand_responses SET status='ACCEPTED', updated_at=? WHERE id=?", (datetime.now().isoformat(timespec='seconds'), response_id)); connection.execute("UPDATE demand_responses SET status='REJECTED', updated_at=? WHERE demand_id=? AND id<>? AND status IN ('SUBMITTED','SHORTLISTED')", (datetime.now().isoformat(timespec='seconds'), demand_id, response_id)); connection.execute("UPDATE demands SET status='ORDER_CREATED', updated_at=? WHERE id=?", (datetime.now().isoformat(timespec='seconds'), demand_id)); connection.execute('''INSERT INTO orders (id,harvest_id,farmer_id,buyer_name,buyer_type,quantity,unit,total_amount,status,payment_status,transaction_signature) VALUES (?,?,?,?,?,?,?,?,'PENDING_PAYMENT','PENDING',NULL)''', (order_id, harvest['id'], response['farmer_id'], demand['buyer_name'], demand['buyer_type'], response['quantity_offered'], demand['unit'], total)); connection.execute('INSERT INTO deliveries (id,order_id,status) VALUES (?,?,?)', (f'delivery-{order_id}', order_id, 'PENDING')); connection.commit(); order = dict(connection.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()); connection.close(); return ok(order, 201)

@app.get('/api/buyers/<buyer_id>/profile')
def get_buyer_profile(buyer_id):
    connection = get_connection(); buyer = connection.execute('SELECT * FROM buyer_profiles WHERE id=? OR business_name=?', (buyer_id, buyer_id)).fetchone()
    if not buyer: connection.close(); return fail('Buyer profile not found', 404)
    completed = connection.execute("SELECT COUNT(*) AS count FROM orders WHERE buyer_name=? AND payment_status='PAID'", (buyer['business_name'],)).fetchone()['count']; payments = connection.execute("SELECT COUNT(*) AS count FROM payments p JOIN orders o ON o.id=p.order_id WHERE o.buyer_name=? AND p.status='VERIFIED'", (buyer['business_name'],)).fetchone()['count']; deliveries = connection.execute("SELECT COUNT(*) AS count FROM deliveries d JOIN orders o ON o.id=d.order_id WHERE o.buyer_name=? AND d.status='DELIVERED'", (buyer['business_name'],)).fetchone()['count']; connection.close(); return ok({**dict(buyer), 'completed_orders': completed, 'verified_payments': payments, 'delivery_completions': deliveries})

@app.get('/api/farmers/<farmer_id>/opportunities')
def farmer_opportunities(farmer_id):
    return ok(rows("SELECT * FROM demands WHERE status IN ('OPEN','RESPONSES_RECEIVED') AND id NOT IN (SELECT demand_id FROM demand_responses WHERE farmer_id=? AND status IN ('SUBMITTED','ACCEPTED')) ORDER BY created_at DESC", (farmer_id,)))

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
      VALUES (?,?,?,?,?,?,?,?,'PENDING_PAYMENT','PENDING',NULL)''', (order_id, listing['harvest_id'], listing['farmer_id'], data['buyer_name'], data.get('buyer_type', 'RETAILER'), quantity, listing['unit'], total))
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

@app.post('/api/orders/<order_id>/payment-intent')
def payment_intent(order_id):
    data = request.get_json(silent=True) or {}
    payer_wallet = str(data.get('payer_wallet', '')).strip()
    if not valid_solana_address(payer_wallet): return fail('A valid buyer wallet is required.')
    connection = get_connection()
    order = connection.execute('SELECT o.*, f.wallet_address AS recipient_wallet FROM orders o JOIN farmers f ON f.id=o.farmer_id WHERE o.id=?', (order_id,)).fetchone()
    if not order: connection.close(); return fail('Order not found', 404)
    existing = connection.execute("SELECT * FROM payments WHERE order_id=? AND status='VERIFIED'", (order_id,)).fetchone()
    if existing: connection.close(); return ok({'state': 'VERIFIED', 'payment': dict(existing), 'explorer_url': explorer_url(existing['transaction_signature'])})
    processing = connection.execute("SELECT * FROM payments WHERE order_id=? AND status='PROCESSING'", (order_id,)).fetchone()
    if processing: connection.close(); return fail('A payment is already processing for this order.', 409)
    if order['status'] in {'PAID', 'COMPLETED'} or order['payment_status'] == 'PAID': connection.close(); return fail('This order has already been paid.', 409)
    if not valid_solana_address(order['recipient_wallet']): connection.close(); return fail('This seller has not connected a settlement wallet yet.', 409)
    payment_id = f'payment-{order_id}'
    failed = connection.execute("SELECT id FROM payments WHERE order_id=? AND status='FAILED'", (order_id,)).fetchone()
    if failed:
        connection.execute("UPDATE payments SET payer_wallet=?, recipient_wallet=?, amount_sol=?, network='devnet', transaction_signature=NULL, block_time=NULL, verified_at=NULL, status='PROCESSING' WHERE id=?", (payer_wallet, order['recipient_wallet'], DEMO_SOL_AMOUNT, failed['id']))
    else:
        connection.execute('INSERT INTO payments (id,order_id,payer_wallet,recipient_wallet,amount_sol,network,status) VALUES (?,?,?,?,?,?,?)', (payment_id, order_id, payer_wallet, order['recipient_wallet'], DEMO_SOL_AMOUNT, 'devnet', 'PROCESSING'))
    connection.execute("UPDATE orders SET status='PAYMENT_PROCESSING' WHERE id=?", (order_id,)); connection.commit(); connection.close()
    return ok({'state': 'AWAITING_WALLET_APPROVAL', 'payment_id': payment_id, 'order_id': order_id, 'amount_sol': DEMO_SOL_AMOUNT, 'network': 'devnet', 'recipient_wallet': order['recipient_wallet']})

@app.post('/api/orders/<order_id>/verify-payment')
def verify_payment(order_id):
    data = request.get_json(silent=True) or {}
    signature = str(data.get('transaction_signature', '')).strip(); payer_wallet = str(data.get('payer_wallet', '')).strip()
    if not signature or not valid_solana_address(payer_wallet) or data.get('network') != 'devnet': return fail('Payment signature, buyer wallet, and Devnet network are required.')
    connection = get_connection()
    order = connection.execute('SELECT o.*, f.wallet_address AS recipient_wallet FROM orders o JOIN farmers f ON f.id=o.farmer_id WHERE o.id=?', (order_id,)).fetchone()
    if not order: connection.close(); return fail('Order not found', 404)
    existing_signature = connection.execute('SELECT * FROM payments WHERE transaction_signature=?', (signature,)).fetchone()
    if existing_signature:
        if existing_signature['order_id'] != order_id:
            connection.close(); return fail('This transaction signature has already been used for another order.', 409)
        if existing_signature['status'] == 'VERIFIED':
            result = dict(existing_signature); connection.close(); result.update({'state': 'VERIFIED', 'explorer_url': explorer_url(signature)}); return ok(result)
    payment = connection.execute("SELECT * FROM payments WHERE order_id=? AND status='PROCESSING'", (order_id,)).fetchone()
    if not payment or payment['payer_wallet'] != payer_wallet or payment['network'] != 'devnet': connection.close(); return fail('Payment could not be verified.')
    if not valid_solana_address(order['recipient_wallet']): connection.close(); return fail('Seller settlement wallet is missing or does not match.')
    try:
        tx = rpc_call('getTransaction', [signature, {'encoding': 'jsonParsed', 'commitment': 'confirmed', 'maxSupportedTransactionVersion': 0}])
        if not tx or tx.get('meta', {}).get('err') is not None: raise ValueError()
        statuses = rpc_call('getSignatureStatuses', [[signature], {'searchTransactionHistory': True}]) or {}
        confirmation = (statuses.get('value') or [None])[0] or {}
        if confirmation.get('err') is not None or confirmation.get('confirmationStatus') not in ('confirmed', 'finalized'): raise ValueError()
        account_keys = [item.get('pubkey') if isinstance(item, dict) else item for item in tx.get('transaction', {}).get('message', {}).get('accountKeys', [])]
        valid_transfer = False
        expected_lamports = int(round(float(payment['amount_sol']) * 1_000_000_000))
        for instruction in tx.get('transaction', {}).get('message', {}).get('instructions', []):
            parsed = instruction.get('parsed', {}) if isinstance(instruction, dict) else {}; info = parsed.get('info', {})
            if parsed.get('type') == 'transfer' and info.get('source') == payer_wallet and info.get('destination') == payment['recipient_wallet'] and int(info.get('lamports', 0)) == expected_lamports: valid_transfer = True
        if not account_keys or account_keys[0] != payer_wallet or payment['recipient_wallet'] != order['recipient_wallet'] or not valid_transfer: raise ValueError()
    except Exception:
        mark_payment_failed(connection, payment['id'])
        connection.execute("UPDATE orders SET status='PAYMENT_FAILED' WHERE id=? AND payment_status='PENDING'", (order_id,)); connection.commit()
        connection.close(); return fail('Blockchain verification is temporarily unavailable. Your order remains unpaid until verification succeeds.')
    now = datetime.now().isoformat(timespec='seconds')
    try:
        connection.execute("UPDATE payments SET transaction_signature=?, status='VERIFIED', block_time=?, verified_at=? WHERE id=?", (signature, tx.get('blockTime'), now, payment['id']))
    except Exception:
        connection.rollback(); connection.close(); return fail('This transaction signature has already been consumed.', 409)
    connection.execute("UPDATE orders SET status='PAID', payment_status='PAID', transaction_signature=? WHERE id=?", (signature, order_id))
    connection.execute('UPDATE economic_credentials SET evidence_count=evidence_count+1, verified_transaction_count=verified_transaction_count+1, updated_at=? WHERE farmer_id=?', (now, order['farmer_id']))
    connection.execute("UPDATE crop_batch_credentials SET status='VERIFIED', network='devnet', wallet_address=?, transaction_signature=?, verified_at=?, updated_at=? WHERE harvest_id=?", (payment['recipient_wallet'], signature, now, now, order['harvest_id']))
    connection.commit(); result = dict(connection.execute('SELECT * FROM payments WHERE id=?', (payment['id'],)).fetchone()); connection.close()
    result['state'] = 'VERIFIED'; result['explorer_url'] = explorer_url(signature)
    return ok(result)

@app.post('/api/orders/<order_id>/cancel-payment')
def cancel_payment(order_id):
    connection = get_connection()
    payment = connection.execute("SELECT id FROM payments WHERE order_id=? AND status='PROCESSING'", (order_id,)).fetchone()
    if payment:
        connection.execute("UPDATE payments SET status='FAILED' WHERE id=?", (payment['id'],))
        connection.execute("UPDATE orders SET status='PENDING_PAYMENT' WHERE id=? AND payment_status='PENDING'", (order_id,))
        connection.commit()
    connection.close(); return ok({'state': 'FAILED', 'order_id': order_id})

@app.get('/api/orders/<order_id>/payment')
def get_payment(order_id):
    item = row('SELECT * FROM payments WHERE order_id=?', (order_id,))
    if item and item.get('transaction_signature'): item['explorer_url'] = explorer_url(item['transaction_signature'])
    return ok(item)

@app.get('/api/farmers/<farmer_id>/economic-credential')
def get_economic_credential(farmer_id):
    connection = get_connection(); snapshot = credential_snapshot(connection, farmer_id); item = connection.execute('SELECT * FROM economic_credentials WHERE farmer_id=?', (farmer_id,)).fetchone(); digital_credentials = [crop_batch_credential_payload(dict(row)) for row in connection.execute('SELECT * FROM crop_batch_credentials WHERE farmer_id=? ORDER BY created_at DESC', (farmer_id,)).fetchall()]; connection.close()
    return ok({**dict(item), **snapshot, 'digital_credentials': digital_credentials}) if item and snapshot else fail('Economic credential not found', 404)

@app.get('/api/credentials/<credential_id>')
def get_credential(credential_id):
    connection = get_connection(); item = connection.execute('SELECT * FROM economic_credentials WHERE credential_id=?', (credential_id,)).fetchone()
    if not item: connection.close(); return fail('Credential not found', 404)
    snapshot = credential_snapshot(connection, item['farmer_id']); item = connection.execute('SELECT * FROM economic_credentials WHERE credential_id=?', (credential_id,)).fetchone(); digital_credentials = [crop_batch_credential_payload(dict(row)) for row in connection.execute('SELECT * FROM crop_batch_credentials WHERE farmer_id=? ORDER BY created_at DESC', (item['farmer_id'],)).fetchall()]; connection.close()
    return ok({**dict(item), 'verified_harvests': snapshot['verified_harvests'], 'completed_sales': snapshot['completed_sales'], 'verified_payments': snapshot['verified_payments'], 'verified_deliveries': snapshot['verified_deliveries'], 'verified_trade_value': snapshot['verified_trade_value'], 'digital_credentials': digital_credentials})

@app.get('/api/farmers/<farmer_id>/passport/activity')
def get_passport_activity(farmer_id):
    connection = get_connection(); rows = credential_evidence(connection, farmer_id); connection.close(); return ok(rows)

@app.get('/api/farmers/<farmer_id>/passport/evidence')
def get_passport_evidence(farmer_id):
    connection = get_connection(); rows = credential_evidence(connection, farmer_id); connection.close(); return ok(rows)

@app.post('/api/credentials/<credential_id>/share')
def share_credential(credential_id):
    data = request.get_json(silent=True) or {}; allowed = {'harvests', 'sales', 'payments', 'deliveries'}; selected = [item for item in data.get('categories', list(allowed)) if item in allowed]
    if not selected: return fail('Select at least one evidence category.')
    item = row('SELECT credential_id, version, status, fingerprint, farmer_id FROM economic_credentials WHERE credential_id=?', (credential_id,))
    if not item: return fail('Credential not found', 404)
    return ok({'credential_id': item['credential_id'], 'version': item['version'], 'status': item['status'], 'fingerprint': item['fingerprint'], 'categories': selected, 'share_url': f'/verify/{item["credential_id"]}?categories={",".join(selected)}'})

@app.get('/api/farmers/<farmer_id>/passport')
def get_passport(farmer_id):
    connection = get_connection(); snapshot = credential_snapshot(connection, farmer_id); evidence = credential_evidence(connection, farmer_id); credential = connection.execute('SELECT * FROM economic_credentials WHERE farmer_id=?', (farmer_id,)).fetchone(); digital_credentials = [crop_batch_credential_payload(dict(row)) for row in connection.execute('SELECT * FROM crop_batch_credentials WHERE farmer_id=? ORDER BY created_at DESC', (farmer_id,)).fetchall()]; connection.close()
    if not snapshot: return fail('Farmer not found', 404)
    return ok({**snapshot, 'credential': dict(credential) if credential else None, 'activity': evidence, 'digital_credentials': digital_credentials})

@app.get('/api/market-intelligence')
def get_market_intelligence():
    connection = get_connection()
    payload = _market_intelligence_payload(connection)
    connection.close()
    return ok(payload)

def _count(connection, query, params=()):
    return connection.execute(query, params).fetchone()[0]


def _openrouter_response(model_name, payload):
    if not OPENROUTER_API_KEY:
        raise ValueError('OPENROUTER_API_KEY is not configured.')
    request_data = {
        'model': model_name,
        'messages': [{
            'role': 'user',
            'content': payload,
        }],
        'temperature': 0.2,
        'top_p': 0.9,
    }
    req = urllib.request.Request(
        OPENROUTER_BASE_URL,
        data=json.dumps(request_data).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://cropcred.local',
            'X-Title': 'CropCred Market Intelligence',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        body = json.loads(response.read().decode('utf-8'))
    if body.get('error'):
        raise ValueError(str(body['error']))
    try:
        return body['choices'][0]['message']['content']
    except (KeyError, TypeError, IndexError):
        return body.get('choices', [{}])[0].get('text', '')


def _parse_ai_insights(raw_text):
    text = (raw_text or '').strip()
    if not text:
        raise ValueError('Empty OpenRouter response.')
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            parsed = parsed.get('insights', [])
        if not isinstance(parsed, list):
            raise ValueError('OpenRouter response did not contain a list of insights.')
        normalized = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            if not item.get('text'):
                continue
            normalized.append({
                'title': item.get('title', 'CropCred insight'),
                'text': item['text'],
                'source': 'CropCred records',
                'type': 'AI-generated insight',
            })
        if normalized:
            return normalized
        raise ValueError('No valid insights produced by OpenRouter.')
    except json.JSONDecodeError:
        fallback = []
        for chunk in re.split(r'\n\s*\n|\s*\*\s*', text):
            candidate = chunk.strip()
            if candidate and len(candidate) > 20:
                fallback.append({
                    'title': 'AI insight',
                    'text': candidate.replace('Source:', '').replace('Type:', '').strip(),
                    'source': 'CropCred records',
                    'type': 'AI-generated insight',
                })
        if fallback:
            return fallback[:3]
        raise ValueError('OpenRouter response was not valid JSON or insight text.')


def _build_rule_based_insights(crop_demand, price_observations):
    if not crop_demand or not price_observations.get('transaction_count'):
        return [{
            'title': 'Market intelligence unavailable',
            'text': 'Insufficient CropCred data for a reliable insight.',
            'source': 'CropCred records',
            'type': 'Data-derived insight',
        }]
    top_crop = max(crop_demand, key=lambda item: (item['demand_count'], item['available_quantity']))
    strongest_supply = max(crop_demand, key=lambda item: item['available_quantity'])
    average_price = price_observations.get('average_observed_price')
    return [
        {
            'title': 'Demand concentration',
            'text': f"{top_crop['crop']} demand is currently concentrated around the available CropCred listings.",
            'source': 'CropCred records',
            'type': 'Data-derived insight',
        },
        {
            'title': 'Supply coverage',
            'text': f"{strongest_supply['crop']} has the broadest observed available CropCred supply across recorded batches.",
            'source': 'CropCred records',
            'type': 'Data-derived insight',
        },
        {
            'title': 'Observed pricing',
            'text': f"Observed CropCred pricing for the current order history averages ₹{average_price} per unit across {price_observations.get('transaction_count')} recorded transactions.",
            'source': 'CropCred records',
            'type': 'Data-derived insight',
        },
    ]


def _market_intelligence_payload(connection):
    active_crop_batches = connection.execute("SELECT * FROM crop_batches WHERE availability_status IN ('AVAILABLE','RESERVED')").fetchall()
    active_demands = connection.execute('SELECT COUNT(*) AS count FROM demands').fetchone()['count']
    open_auctions = connection.execute("SELECT COUNT(*) AS count FROM crop_auctions WHERE status IN ('OPEN','OFFER_RECEIVED')").fetchone()['count']
    completed_orders = connection.execute("SELECT COUNT(*) AS count FROM orders WHERE payment_status='PAID' OR status IN ('COMPLETED','DELIVERED')").fetchone()['count']
    observed_trade_value = connection.execute("SELECT COALESCE(SUM(total_amount),0) AS value FROM orders WHERE payment_status='PAID'").fetchone()['value']
    available_supply = sum(float(item['quantity']) for item in active_crop_batches)

    demand_rows = connection.execute('SELECT crop, COUNT(*) AS demand_count, COALESCE(SUM(quantity),0) AS demand_quantity FROM demands GROUP BY crop ORDER BY demand_count DESC, demand_quantity DESC').fetchall()
    supply_rows = connection.execute("SELECT crop_name AS crop, COALESCE(SUM(quantity),0) AS available_quantity FROM crop_batches WHERE availability_status IN ('AVAILABLE','RESERVED') GROUP BY crop_name ORDER BY available_quantity DESC").fetchall()
    order_rows = connection.execute("SELECT h.crop, COUNT(*) AS completed_orders FROM orders o JOIN harvests h ON h.id=o.harvest_id WHERE o.payment_status='PAID' OR o.status IN ('COMPLETED','DELIVERED') GROUP BY h.crop ORDER BY completed_orders DESC").fetchall()

    crop_names = sorted({row['crop'] for row in demand_rows} | {row['crop'] for row in supply_rows} | {row['crop'] for row in order_rows})
    crop_demand = []
    price_rows = connection.execute("SELECT o.total_amount / NULLIF(o.quantity,0) AS observed_price, h.crop, o.unit FROM orders o JOIN harvests h ON h.id=o.harvest_id WHERE o.payment_status='PAID' AND o.quantity > 0 ORDER BY o.created_at DESC").fetchall()

    for crop in crop_names:
        demand_row = next((item for item in demand_rows if item['crop'] == crop), None)
        supply_row = next((item for item in supply_rows if item['crop'] == crop), None)
        order_row = next((item for item in order_rows if item['crop'] == crop), None)
        prices = [float(item['observed_price']) for item in price_rows if item['crop'] == crop]
        crop_demand.append({
            'crop': crop,
            'demand_count': int(demand_row['demand_count']) if demand_row else 0,
            'available_quantity': float(supply_row['available_quantity']) if supply_row else 0.0,
            'completed_orders': int(order_row['completed_orders']) if order_row else 0,
            'observed_price_min': round(min(prices), 2) if prices else None,
            'observed_price_max': round(max(prices), 2) if prices else None,
            'observed_price_average': round(sum(prices) / len(prices), 2) if prices else None,
            'observed_price_count': len(prices),
        })

    observed_prices = [float(item['observed_price']) for item in price_rows]
    observed_min = min(observed_prices) if observed_prices else None
    observed_max = max(observed_prices) if observed_prices else None
    observed_average = sum(observed_prices) / len(observed_prices) if observed_prices else None

    overview = {
        'active_crop_batches': len(active_crop_batches),
        'available_supply': round(available_supply, 2),
        'active_demands': active_demands,
        'open_auctions': open_auctions,
        'completed_orders': completed_orders,
        'observed_trade_value': round(float(observed_trade_value), 2),
    }

    price_observations = {
        'minimum_observed_price': round(observed_min, 2) if observed_min is not None else None,
        'maximum_observed_price': round(observed_max, 2) if observed_max is not None else None,
        'average_observed_price': round(observed_average, 2) if observed_average is not None else None,
        'transaction_count': len(observed_prices),
    }

    if not crop_demand and not observed_prices:
        insights = [{
            'title': 'Market intelligence unavailable',
            'text': 'Insufficient CropCred data for a reliable insight.',
            'source': 'CropCred records',
            'type': 'Data-derived insight',
        }]
    else:
        base_insights = _build_rule_based_insights(crop_demand, price_observations)
        insights = base_insights
        if OPENROUTER_API_KEY:
            prompt = (
                'You are generating CropCred market intelligence from actual records only. ' +
                'Never invent farmers, prices, demand, supply, or transactions. Base your answer only on this JSON. ' +
                'Return valid JSON as an array of objects with keys title, text, type, source. ' +
                'Each text must mention that the evidence comes from CropCred records. ' +
                'Use exactly the source value "CropCred records" and type value "AI-generated insight". ' +
                'If there is insufficient data, output one object with text "Insufficient CropCred data for a reliable insight." and type "Data-derived insight". ' +
                'Do not claim guaranteed prices, forecast, or buying decisions.\n\n' +
                json.dumps({
                    'overview': overview,
                    'crop_demand': sorted(crop_demand, key=lambda item: (-item['demand_count'], -item['available_quantity'], item['crop'])),
                    'price_observations': price_observations,
                }, separators=(',', ':'))
            )
            try:
                model_candidates = [OPENROUTER_FREE_MODEL, OPENROUTER_BEST_MODEL]
                for model_name in model_candidates:
                    try:
                        raw = _openrouter_response(model_name, prompt)
                        insights = _parse_ai_insights(raw)
                        break
                    except Exception:
                        continue
            except Exception:
                insights = base_insights

    payload = {
        'overview': overview,
        'crop_demand': sorted(crop_demand, key=lambda item: (-item['demand_count'], -item['available_quantity'], item['crop'])),
        'price_observations': price_observations,
        'insights': insights,
        'source': 'CropCred records',
    }

    connection.execute('DELETE FROM market_insights')
    for index, insight in enumerate(payload['insights'], start=1):
        connection.execute(
            'INSERT INTO market_insights (id, category, title, summary, source, insight_type, data_json) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (
                f'MI-{index:04d}',
                'market_intelligence',
                insight['title'],
                insight['text'],
                insight['source'],
                insight['type'],
                json.dumps({
                    'overview': overview,
                    'crop_demand': payload['crop_demand'],
                    'price_observations': price_observations,
                    'insight_title': insight['title'],
                }, separators=(',', ':')),
            ),
        )
    connection.commit()
    return payload


def insights_snapshot():
    connection = get_connection()
    verified_harvests = _count(connection, "SELECT COUNT(*) FROM harvests WHERE status='VERIFIED'")
    orders = _count(connection, 'SELECT COUNT(*) FROM orders')
    paid_orders = _count(connection, "SELECT COUNT(*) FROM orders WHERE payment_status='PAID'")
    completed_orders = _count(connection, "SELECT COUNT(*) FROM orders WHERE status IN ('COMPLETED','DELIVERED')")
    verified_payments = _count(connection, "SELECT COUNT(*) FROM payments WHERE status='VERIFIED'")
    deliveries = _count(connection, "SELECT COUNT(*) FROM deliveries WHERE status='DELIVERED'")
    credentials = _count(connection, 'SELECT COUNT(*) FROM economic_credentials')
    evidence = _count(connection, 'SELECT COUNT(*) FROM credential_evidence WHERE verified=1')
    verification_events = _count(connection, 'SELECT COUNT(*) FROM credential_verification_events')
    successful_verifications = _count(connection, 'SELECT COUNT(*) FROM credential_verification_events WHERE success=1')
    active_buyers = _count(connection, 'SELECT COUNT(DISTINCT buyer_name) FROM orders')
    active_farmers = _count(connection, 'SELECT COUNT(DISTINCT farmer_id) FROM harvests')
    demands = _count(connection, 'SELECT COUNT(*) FROM demands')
    open_demands = _count(connection, "SELECT COUNT(*) FROM demands WHERE status IN ('OPEN','RESPONSES_RECEIVED')")
    responses = _count(connection, 'SELECT COUNT(*) FROM demand_responses')
    b2b_orders = _count(connection, "SELECT COUNT(*) FROM orders o WHERE o.buyer_name IN (SELECT buyer_name FROM demands) AND o.status IN ('COMPLETED','DELIVERED')")
    listed_quantity = connection.execute('SELECT COALESCE(SUM(quantity_available),0) FROM marketplace_listings').fetchone()[0]
    total_listed = listed_quantity
    demand_quantity = connection.execute('SELECT COALESCE(SUM(quantity),0) FROM demands').fetchone()[0]
    repeat_buyers = _count(connection, 'SELECT COUNT(*) FROM (SELECT buyer_name FROM orders GROUP BY buyer_name HAVING COUNT(*) > 1)')
    avg_order = connection.execute('SELECT AVG(quantity) FROM orders').fetchone()[0]
    crop_volume = [dict(item) for item in connection.execute("SELECT h.crop, SUM(o.quantity) AS quantity, COUNT(o.id) AS orders FROM orders o JOIN harvests h ON h.id=o.harvest_id GROUP BY h.crop ORDER BY quantity DESC").fetchall()]
    status_mix = [dict(item) for item in connection.execute('SELECT status, COUNT(*) AS count FROM orders GROUP BY status ORDER BY count DESC').fetchall()]
    evidence_types = [dict(item) for item in connection.execute('SELECT evidence_type, COUNT(*) AS count FROM credential_evidence GROUP BY evidence_type ORDER BY count DESC').fetchall()]
    validation = _count(connection, 'SELECT COUNT(*) FROM validation_interviews')
    pilots = _count(connection, 'SELECT COUNT(*) FROM pilot_participants')
    external_traction = _count(connection, "SELECT COUNT(*) FROM pilot_participants WHERE stage='PILOT ACTIVE'")
    connection.close()
    return {'product_activity': {'verified_harvests': verified_harvests, 'completed_sales': completed_orders, 'verified_payments': verified_payments, 'deliveries': deliveries, 'credentials': credentials, 'evidence_records': evidence, 'verification_events': verification_events, 'active_buyers': active_buyers, 'active_farmers': active_farmers, 'b2b_demands': demands, 'b2b_responses': responses, 'completed_b2b_transactions': b2b_orders}, 'validation': {'conversations': validation}, 'pilots': {'participants': pilots}, 'external_traction': {'recorded': external_traction, 'label': 'External traction recorded' if external_traction else 'No external traction recorded yet'}, 'funnel': [{'label':'Farmers', 'value': active_farmers}, {'label':'Harvests registered', 'value': _count(get_connection(), 'SELECT COUNT(*) FROM harvests')}, {'label':'Orders', 'value': orders}, {'label':'Verified payments', 'value': verified_payments}, {'label':'Deliveries confirmed', 'value': deliveries}, {'label':'Economic credentials', 'value': credentials}, {'label':'Credential verification events', 'value': verification_events}], 'commerce': {'total_listed_quantity': total_listed, 'active_listing_quantity': listed_quantity, 'completed_orders': completed_orders, 'repeat_buyer_activity': repeat_buyers, 'average_order_quantity': avg_order, 'demand_volume': demand_quantity, 'top_crops': crop_volume, 'order_status': status_mix}, 'b2b': {'open_demands': open_demands, 'total_demands': demands, 'responses': responses, 'demand_quantity': demand_quantity, 'completed_transactions': b2b_orders, 'response_rate': round(responses / demands * 100) if demands else None, 'demand_to_order_conversion': round(b2b_orders / demands * 100) if demands else None}, 'credentials': {'issued': credentials, 'verified': _count(get_connection(), "SELECT COUNT(*) FROM economic_credentials WHERE status='VERIFIED'"), 'verification_attempts': verification_events, 'successful_verifications': successful_verifications, 'success_rate': round(successful_verifications / verification_events * 100) if verification_events else None, 'blockchain_anchored': _count(get_connection(), "SELECT COUNT(*) FROM economic_credentials WHERE onchain_reference IS NOT NULL AND onchain_reference != ''"), 'evidence_types': evidence_types}}

@app.get('/api/insights/overview')
def insights_overview(): return ok(insights_snapshot())
@app.get('/api/insights/product-funnel')
def insights_funnel(): return ok(insights_snapshot()['funnel'])
@app.get('/api/insights/commerce')
def insights_commerce(): return ok(insights_snapshot()['commerce'])
@app.get('/api/insights/b2b')
def insights_b2b(): return ok(insights_snapshot()['b2b'])
@app.get('/api/insights/credentials')
def insights_credentials(): return ok(insights_snapshot()['credentials'])

def _records(table): return rows(f'SELECT * FROM {table} ORDER BY created_at DESC')
def _create_record(table, fields, required):
    data = request.get_json(silent=True) or {}
    if any(data.get(key) in (None, '') for key in required): return fail(f"Required fields missing: {', '.join(required)}")
    connection = get_connection(); record_id = f"{table[:4].upper()}-{_count(connection, f'SELECT COUNT(*) FROM {table}') + 1:04d}"
    values = [data.get(field) for field in fields]; columns = ','.join(['id', *fields]); placeholders = ','.join(['?'] * (len(fields) + 1))
    try:
        connection.execute(f'INSERT INTO {table} ({columns}) VALUES ({placeholders})', [record_id, *values]); connection.commit(); item = dict(connection.execute(f'SELECT * FROM {table} WHERE id=?', (record_id,)).fetchone()); return ok(item, 201)
    except Exception as exc: return fail('Could not save record. Check the submitted fields.', 400)
    finally: connection.close()

@app.get('/api/validation/interviews')
def get_validation_interviews(): return ok(_records('validation_interviews'))
@app.post('/api/validation/interviews')
def create_validation_interview(): return _create_record('validation_interviews', ['participant_type','participant_name_or_alias','region','date','current_workflow','pain_point','problem_confirmed','requested_capability','pilot_interest','notes'], ['participant_type','date','pain_point','problem_confirmed','pilot_interest'])
@app.get('/api/product-learnings')
def get_product_learnings(): return ok(_records('product_learnings'))
@app.post('/api/product-learnings')
def create_product_learning(): return _create_record('product_learnings', ['insight','source','product_change','result','status','date'], ['insight','source','status','date'])
@app.get('/api/pilots')
def get_pilots(): return ok(_records('pilot_participants'))
@app.post('/api/pilots')
def create_pilot(): return _create_record('pilot_participants', ['organization_or_alias','participant_type','region','stage','interest_area','next_action','notes'], ['organization_or_alias','participant_type','stage'])
@app.get('/api/gtm-experiments')
def get_gtm_experiments(): return ok(_records('gtm_experiments'))
@app.post('/api/gtm-experiments')
def create_gtm_experiment(): return _create_record('gtm_experiments', ['experiment_name','target_segment','hypothesis','channel','metric','result','status','date'], ['experiment_name','status','date'])
@app.get('/api/founder-notes')
def get_founder_notes(): return ok(_records('founder_notes'))
@app.post('/api/founder-notes')
def create_founder_note(): return _create_record('founder_notes', ['decision','reasoning','evidence','date'], ['decision','date'])
@app.get('/api/credential-verification-events')
def get_verification_events(): return ok(_records('credential_verification_events'))
@app.post('/api/credential-verification-events')
def create_verification_event(): return _create_record('credential_verification_events', ['credential_id','verifier_type','event_type','timestamp','success'], ['credential_id','verifier_type','event_type','timestamp'])

if __name__ == '__main__':
    init_db(); seed_db(); app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=False)
