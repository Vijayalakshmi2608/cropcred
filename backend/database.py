from pathlib import Path
import hashlib
import json
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'cropcred.db'

SCHEMA = '''
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS farmers (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  location TEXT NOT NULL,
  primary_crops TEXT NOT NULL,
  farm_size TEXT NOT NULL,
  wallet_address TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS harvests (
  id TEXT PRIMARY KEY,
  farmer_id TEXT NOT NULL REFERENCES farmers(id),
  crop TEXT NOT NULL,
  quantity REAL NOT NULL CHECK(quantity > 0),
  unit TEXT NOT NULL,
  harvest_date TEXT NOT NULL,
  expected_price REAL NOT NULL CHECK(expected_price >= 0),
  location TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL CHECK(status IN ('REGISTERED','PENDING','VERIFIED')),
  proof_hash TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS crop_batches (
  id TEXT PRIMARY KEY,
  farmer_id TEXT NOT NULL REFERENCES farmers(id),
  harvest_id TEXT NOT NULL UNIQUE REFERENCES harvests(id),
  crop_name TEXT NOT NULL,
  variety TEXT NOT NULL,
  quantity REAL NOT NULL CHECK(quantity > 0),
  unit TEXT NOT NULL,
  harvest_date TEXT NOT NULL,
  expected_price_min REAL NOT NULL CHECK(expected_price_min >= 0),
  expected_price_max REAL NOT NULL CHECK(expected_price_max >= expected_price_min),
  availability_status TEXT NOT NULL CHECK(availability_status IN ('AVAILABLE','RESERVED','SOLD','UNAVAILABLE')),
  quality_status TEXT NOT NULL CHECK(quality_status IN ('PENDING','SELF_DECLARED','CERTIFICATION_PENDING','CERTIFIED')),
  fingerprint TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS crop_batch_credentials (
  id TEXT PRIMARY KEY,
  batch_id TEXT NOT NULL UNIQUE REFERENCES crop_batches(id) ON DELETE CASCADE,
  crop_id TEXT NOT NULL,
  farmer_id TEXT NOT NULL REFERENCES farmers(id),
  farmer_identity_ref TEXT NOT NULL,
  crop_type TEXT NOT NULL,
  quantity REAL NOT NULL CHECK(quantity >= 0),
  unit TEXT NOT NULL,
  harvest_id TEXT NOT NULL,
  harvest_date TEXT NOT NULL,
  harvest_location TEXT,
  evidence_hash TEXT NOT NULL,
  metadata_hash TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('PENDING','VERIFIED','UNVERIFIED')),
  network TEXT NOT NULL DEFAULT 'devnet',
  wallet_address TEXT,
  transaction_signature TEXT,
  verified_at TEXT,
  metadata_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS crop_auctions (
  id TEXT PRIMARY KEY,
  buyer_name TEXT NOT NULL,
  buyer_type TEXT NOT NULL,
  crop TEXT NOT NULL,
  crop_batch_id TEXT REFERENCES crop_batches(id) ON DELETE CASCADE,
  quantity REAL NOT NULL CHECK(quantity > 0),
  unit TEXT NOT NULL,
  price_min REAL NOT NULL CHECK(price_min >= 0),
  price_max REAL NOT NULL CHECK(price_max >= price_min),
  deadline TEXT NOT NULL,
  delivery_location TEXT NOT NULL,
  quality_requirements TEXT,
  evidence_requirements TEXT,
  status TEXT NOT NULL CHECK(status IN ('DRAFT','OPEN','OFFER_RECEIVED','CLOSED','AWARDED','CANCELLED')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS auction_offers (
  id TEXT PRIMARY KEY,
  auction_id TEXT NOT NULL REFERENCES crop_auctions(id) ON DELETE CASCADE,
  farmer_id TEXT NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
  crop_batch_id TEXT REFERENCES crop_batches(id) ON DELETE CASCADE,
  quantity REAL NOT NULL CHECK(quantity > 0),
  offered_price REAL NOT NULL CHECK(offered_price >= 0),
  delivery_estimate TEXT NOT NULL,
  message TEXT,
  status TEXT NOT NULL CHECK(status IN ('SUBMITTED','ACCEPTED','REJECTED','WITHDRAWN')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS marketplace_listings (
  id TEXT PRIMARY KEY,
  harvest_id TEXT NOT NULL REFERENCES harvests(id),
  farmer_id TEXT NOT NULL REFERENCES farmers(id),
  crop TEXT NOT NULL,
  quantity_available REAL NOT NULL CHECK(quantity_available >= 0),
  unit TEXT NOT NULL,
  price_per_unit REAL NOT NULL CHECK(price_per_unit >= 0),
  harvest_date TEXT NOT NULL,
  verification_status TEXT NOT NULL,
  location TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS demands (
  id TEXT PRIMARY KEY,
  buyer_name TEXT NOT NULL,
  buyer_type TEXT NOT NULL,
  crop TEXT NOT NULL,
  quantity REAL NOT NULL CHECK(quantity > 0),
  unit TEXT NOT NULL,
  price_min REAL NOT NULL,
  price_max REAL NOT NULL,
  location TEXT NOT NULL,
  frequency TEXT NOT NULL,
  deadline TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS buyer_profiles (
  id TEXT PRIMARY KEY,
  business_name TEXT NOT NULL,
  buyer_type TEXT NOT NULL,
  wallet_address TEXT,
  verification_status TEXT NOT NULL DEFAULT 'VERIFIED',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS demand_responses (
  id TEXT PRIMARY KEY,
  demand_id TEXT NOT NULL REFERENCES demands(id),
  farmer_id TEXT NOT NULL REFERENCES farmers(id),
  quantity_offered REAL NOT NULL CHECK(quantity_offered > 0),
  expected_price REAL NOT NULL CHECK(expected_price >= 0),
  available_date TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('SUBMITTED','SHORTLISTED','ACCEPTED','REJECTED','WITHDRAWN')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  harvest_id TEXT NOT NULL REFERENCES harvests(id),
  farmer_id TEXT NOT NULL REFERENCES farmers(id),
  buyer_name TEXT NOT NULL,
  buyer_type TEXT NOT NULL,
  quantity REAL NOT NULL CHECK(quantity > 0),
  unit TEXT NOT NULL,
  total_amount REAL NOT NULL CHECK(total_amount >= 0),
  status TEXT NOT NULL CHECK(status IN ('PLACED','PENDING_PAYMENT','PAYMENT_PROCESSING','PAID','PROCESSING','READY_FOR_DELIVERY','OUT_FOR_DELIVERY','DELIVERED','COMPLETED','PAYMENT_FAILED','CANCELLED')),
  payment_status TEXT NOT NULL CHECK(payment_status IN ('PENDING','PAID')),
  transaction_signature TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS deliveries (
  id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL UNIQUE REFERENCES orders(id),
  status TEXT NOT NULL CHECK(status IN ('PENDING','DELIVERED')),
  confirmed_at TEXT
);
CREATE TABLE IF NOT EXISTS economic_credentials (
  id TEXT PRIMARY KEY,
  farmer_id TEXT NOT NULL REFERENCES farmers(id),
  credential_id TEXT NOT NULL UNIQUE,
  credential_hash TEXT,
  onchain_reference TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS payments (
  id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL UNIQUE REFERENCES orders(id),
  payer_wallet TEXT NOT NULL,
  recipient_wallet TEXT NOT NULL,
  amount_sol REAL NOT NULL CHECK(amount_sol > 0),
  network TEXT NOT NULL CHECK(network = 'devnet'),
  transaction_signature TEXT UNIQUE,
  status TEXT NOT NULL CHECK(status IN ('PROCESSING','VERIFIED','FAILED')),
  block_time INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  verified_at TEXT
);
CREATE TABLE IF NOT EXISTS credential_evidence (
  id TEXT PRIMARY KEY,
  credential_id TEXT NOT NULL REFERENCES economic_credentials(id),
  evidence_type TEXT NOT NULL,
  reference_type TEXT NOT NULL,
  reference_id TEXT NOT NULL,
  verified INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(credential_id, evidence_type, reference_type, reference_id)
);
CREATE TABLE IF NOT EXISTS validation_interviews (
  id TEXT PRIMARY KEY, participant_type TEXT NOT NULL, participant_name_or_alias TEXT,
  region TEXT, date TEXT NOT NULL, current_workflow TEXT, pain_point TEXT NOT NULL,
  problem_confirmed TEXT NOT NULL, requested_capability TEXT, pilot_interest TEXT NOT NULL,
  notes TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS product_learnings (
  id TEXT PRIMARY KEY, insight TEXT NOT NULL, source TEXT NOT NULL, product_change TEXT,
  result TEXT, status TEXT NOT NULL, date TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS pilot_participants (
  id TEXT PRIMARY KEY, organization_or_alias TEXT NOT NULL, participant_type TEXT NOT NULL,
  region TEXT, stage TEXT NOT NULL, interest_area TEXT, next_action TEXT, notes TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS founder_notes (
  id TEXT PRIMARY KEY, decision TEXT NOT NULL, reasoning TEXT, evidence TEXT,
  date TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS gtm_experiments (
  id TEXT PRIMARY KEY, experiment_name TEXT NOT NULL, target_segment TEXT, hypothesis TEXT,
  channel TEXT, metric TEXT, result TEXT, status TEXT NOT NULL, date TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS credential_verification_events (
  id TEXT PRIMARY KEY, credential_id TEXT NOT NULL REFERENCES economic_credentials(credential_id),
  verifier_type TEXT NOT NULL, event_type TEXT NOT NULL, timestamp TEXT NOT NULL,
  success INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS market_insights (
  id TEXT PRIMARY KEY,
  category TEXT NOT NULL DEFAULT 'market_intelligence',
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'CropCred records',
  insight_type TEXT NOT NULL DEFAULT 'Data-derived insight',
  data_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
'''


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    return connection


def init_db():
    connection = get_connection()
    connection.execute('PRAGMA foreign_keys = OFF')
    crop_batch_credential_sql = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='crop_batch_credentials'").fetchone()
    if crop_batch_credential_sql and crop_batch_credential_sql['sql'] and 'ON DELETE CASCADE' not in crop_batch_credential_sql['sql']:
        connection.execute('ALTER TABLE crop_batch_credentials RENAME TO crop_batch_credentials_legacy')
        connection.execute('''CREATE TABLE crop_batch_credentials (
          id TEXT PRIMARY KEY,
          batch_id TEXT NOT NULL UNIQUE REFERENCES crop_batches(id) ON DELETE CASCADE,
          crop_id TEXT NOT NULL,
          farmer_id TEXT NOT NULL REFERENCES farmers(id),
          farmer_identity_ref TEXT NOT NULL,
          crop_type TEXT NOT NULL,
          quantity REAL NOT NULL CHECK(quantity >= 0),
          unit TEXT NOT NULL,
          harvest_id TEXT NOT NULL,
          harvest_date TEXT NOT NULL,
          harvest_location TEXT,
          evidence_hash TEXT NOT NULL,
          metadata_hash TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('PENDING','VERIFIED','UNVERIFIED')),
          network TEXT NOT NULL DEFAULT 'devnet',
          wallet_address TEXT,
          transaction_signature TEXT,
          verified_at TEXT,
          metadata_json TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )''')
        connection.execute('''INSERT INTO crop_batch_credentials (id,batch_id,crop_id,farmer_id,farmer_identity_ref,crop_type,quantity,unit,harvest_id,harvest_date,harvest_location,evidence_hash,metadata_hash,status,network,wallet_address,transaction_signature,verified_at,metadata_json,created_at,updated_at)
          SELECT id,batch_id,crop_id,farmer_id,farmer_identity_ref,crop_type,quantity,unit,harvest_id,harvest_date,harvest_location,evidence_hash,metadata_hash,status,network,wallet_address,transaction_signature,verified_at,metadata_json,created_at,updated_at FROM crop_batch_credentials_legacy''')
        connection.execute('DROP TABLE crop_batch_credentials_legacy')
    existing = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='orders'").fetchone()
    if existing and existing['sql'] and 'PAYMENT_PROCESSING' not in existing['sql'] and 'status TEXT NOT NULL,' not in existing['sql']:
        connection.execute('ALTER TABLE deliveries RENAME TO deliveries_legacy')
        connection.execute('ALTER TABLE orders RENAME TO orders_legacy')
        connection.execute('''CREATE TABLE orders (
          id TEXT PRIMARY KEY, harvest_id TEXT NOT NULL REFERENCES harvests(id), farmer_id TEXT NOT NULL REFERENCES farmers(id), buyer_name TEXT NOT NULL, buyer_type TEXT NOT NULL, quantity REAL NOT NULL CHECK(quantity > 0), unit TEXT NOT NULL, total_amount REAL NOT NULL CHECK(total_amount >= 0), status TEXT NOT NULL, payment_status TEXT NOT NULL CHECK(payment_status IN ('PENDING','PAID')), transaction_signature TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
        connection.execute('INSERT INTO orders SELECT * FROM orders_legacy')
        connection.execute('''CREATE TABLE deliveries (id TEXT PRIMARY KEY, order_id TEXT NOT NULL UNIQUE REFERENCES orders(id), status TEXT NOT NULL CHECK(status IN ('PENDING','DELIVERED')), confirmed_at TEXT)''')
        connection.execute('INSERT INTO deliveries SELECT * FROM deliveries_legacy')
        connection.execute('DROP TABLE deliveries_legacy')
        connection.execute('DROP TABLE orders_legacy')
    payment_existing = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='payments'").fetchone()
    if payment_existing and payment_existing['sql'] and 'orders_legacy' in payment_existing['sql']:
        connection.execute('ALTER TABLE payments RENAME TO payments_legacy')
    connection.executescript(SCHEMA)
    if connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payments_legacy'").fetchone():
        connection.execute('INSERT OR IGNORE INTO payments SELECT * FROM payments_legacy')
        connection.execute('DROP TABLE payments_legacy')
    credential_columns = {row['name'] for row in connection.execute('PRAGMA table_info(economic_credentials)').fetchall()}
    for name, definition in [('credential_type', "TEXT NOT NULL DEFAULT 'ECONOMIC_CREDENTIAL'"), ('evidence_count', 'INTEGER NOT NULL DEFAULT 0'), ('verified_transaction_count', 'INTEGER NOT NULL DEFAULT 0'), ('version', 'INTEGER NOT NULL DEFAULT 1'), ('status', "TEXT NOT NULL DEFAULT 'VERIFIED'"), ('fingerprint', 'TEXT'), ('updated_at', 'TEXT')]:
        if name not in credential_columns:
            connection.execute(f'ALTER TABLE economic_credentials ADD COLUMN {name} {definition}')
    demand_columns = {row['name'] for row in connection.execute('PRAGMA table_info(demands)').fetchall()}
    for name, definition in [('requirements', 'TEXT'), ('status', "TEXT NOT NULL DEFAULT 'OPEN'"), ('updated_at', 'TEXT')]:
        if name not in demand_columns:
            connection.execute(f'ALTER TABLE demands ADD COLUMN {name} {definition}')
    crop_batch_credential_columns = {row['name'] for row in connection.execute('PRAGMA table_info(crop_batch_credentials)').fetchall()}
    for name, definition in [('network', "TEXT NOT NULL DEFAULT 'devnet'"), ('wallet_address', 'TEXT'), ('transaction_signature', 'TEXT'), ('verified_at', 'TEXT'), ('metadata_json', 'TEXT'), ('updated_at', 'TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP')]:
        if name not in crop_batch_credential_columns:
            connection.execute(f'ALTER TABLE crop_batch_credentials ADD COLUMN {name} {definition}')
    connection.executemany('INSERT OR IGNORE INTO buyer_profiles (id,business_name,buyer_type,verification_status) VALUES (?,?,?,?)', [
        ('buyer-1001', 'Chennai Restaurant Collective', 'RESTAURANT', 'VERIFIED'),
        ('buyer-1002', 'Southstar Grocers', 'RETAILER', 'VERIFIED'),
        ('buyer-1003', 'Harvest Kitchen Co.', 'PROCESSOR', 'VERIFIED'),
        ('buyer-1004', 'The Green Table', 'RESTAURANT', 'VERIFIED'),
        ('buyer-1005', 'Daily Basket', 'RETAILER', 'VERIFIED'),
    ])
    connection.execute('PRAGMA foreign_keys = ON')
    connection.commit()
    connection.close()


def seed_db():
    connection = get_connection()
    try:
        if connection.execute('SELECT COUNT(*) FROM farmers').fetchone()[0] > 0:
            return
        farmers = [
            ('farmer-01', 'Arun Kumar', 'Kanchipuram, Tamil Nadu', 'Tomatoes,Bananas,Coconut', '4.2 acres'),
            ('farmer-02', 'Meena Reddy', 'Chittoor, Andhra Pradesh', 'Bananas,Mangoes,Millets', '6.8 acres'),
            ('farmer-03', 'Ravi Singh', 'Nashik, Maharashtra', 'Onions,Grapes,Tomatoes', '3.1 acres'),
        ]
        connection.executemany('INSERT INTO farmers (id,name,location,primary_crops,farm_size) VALUES (?,?,?,?,?)', farmers)
        harvests = [
            ('CR-HRV-00041','farmer-01','Tomatoes',500,'kg','2026-09-18',35,'Kanchipuram, Tamil Nadu','Open-field tomatoes, graded A.','VERIFIED'),
            ('CR-HRV-00042','farmer-01','Bananas',300,'kg','2026-09-20',42,'Kanchipuram, Tamil Nadu','Robusta bananas at commercial maturity.','PENDING'),
            ('CR-HRV-00039','farmer-01','Coconut',180,'units','2026-09-11',28,'Kanchipuram, Tamil Nadu','Fresh coconut harvest.','VERIFIED'),
            ('CR-HRV-00037','farmer-02','Tomatoes',420,'kg','2026-09-05',32,'Chittoor, Andhra Pradesh','Graded tomatoes for wholesale.','VERIFIED'),
            ('CR-HRV-00036','farmer-02','Mangoes',650,'kg','2026-09-02',58,'Chittoor, Andhra Pradesh','Seasonal mango harvest.','VERIFIED'),
            ('CR-HRV-00035','farmer-03','Onions',240,'kg','2026-08-28',26,'Nashik, Maharashtra','Stored onions, sorted for delivery.','PENDING'),
        ]
        connection.executemany('''INSERT INTO harvests
          (id,farmer_id,crop,quantity,unit,harvest_date,expected_price,location,description,status)
          VALUES (?,?,?,?,?,?,?,?,?,?)''', harvests)
        listing_rows = [
            ('listing-01','CR-HRV-00041','farmer-01','Tomatoes',500,'kg',35,'2026-09-18','VERIFIED','Kanchipuram, Tamil Nadu'),
            ('listing-02','CR-HRV-00039','farmer-01','Coconut',180,'units',28,'2026-09-11','VERIFIED','Kanchipuram, Tamil Nadu'),
            ('listing-03','CR-HRV-00037','farmer-02','Tomatoes',420,'kg',32,'2026-09-05','VERIFIED','Chittoor, Andhra Pradesh'),
            ('listing-04','CR-HRV-00036','farmer-02','Mangoes',650,'kg',58,'2026-09-02','VERIFIED','Chittoor, Andhra Pradesh'),
            ('listing-05','CR-HRV-00035','farmer-03','Onions',800,'kg',26,'2026-08-24','VERIFIED','Nashik, Maharashtra'),
            ('listing-06','CR-HRV-00036','farmer-02','Millets',420,'kg',62,'2026-08-22','VERIFIED','Chittoor, Andhra Pradesh'),
            ('listing-07','CR-HRV-00037','farmer-03','Tomatoes',260,'kg',30,'2026-08-20','VERIFIED','Nashik, Maharashtra'),
            ('listing-08','CR-HRV-00042','farmer-01','Bananas',300,'kg',42,'2026-08-19','VERIFIED','Kanchipuram, Tamil Nadu'),
        ]
        connection.executemany('''INSERT INTO marketplace_listings
          (id,harvest_id,farmer_id,crop,quantity_available,unit,price_per_unit,harvest_date,verification_status,location)
          VALUES (?,?,?,?,?,?,?,?,?,?)''', listing_rows)
        crop_batches_seed = [
            ('CRP-1041','farmer-01','CR-HRV-00041','Tomatoes','Ponni',500,'kg','2026-09-18',30,38,'AVAILABLE','CERTIFIED','demo-batch-1041'),
            ('CRP-1042','farmer-02','CR-HRV-00037','Tomatoes','Arka Rakshak',420,'kg','2026-09-05',32,40,'AVAILABLE','CERTIFIED','demo-batch-1042'),
        ]
        connection.executemany('''INSERT OR IGNORE INTO crop_batches
          (id,farmer_id,harvest_id,crop_name,variety,quantity,unit,harvest_date,expected_price_min,expected_price_max,availability_status,quality_status,fingerprint)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''', crop_batches_seed)
        demands = [
            ('DEM-1001','Chennai Restaurant Collective','RESTAURANT','Tomatoes',500,'kg',32,38,'Chennai','Weekly','3 days remaining'),
            ('DEM-1002','Southstar Grocers','RETAILER','Bananas',1000,'kg',38,44,'Bengaluru','Weekly','Weekly requirement'),
            ('DEM-1003','Harvest Kitchen Co.','PROCESSOR','Tomatoes',2000,'kg',29,34,'Coimbatore','Monthly','8 days remaining'),
            ('DEM-1004','The Green Table','RESTAURANT','Coconut',300,'units',25,30,'Pondicherry','Weekly','5 days remaining'),
            ('DEM-1005','Daily Basket','RETAILER','Onions',750,'kg',24,28,'Chennai','Weekly','12 days remaining'),
        ]
        connection.executemany('''INSERT OR IGNORE INTO demands
          (id,buyer_name,buyer_type,crop,quantity,unit,price_min,price_max,location,frequency,deadline)
          VALUES (?,?,?,?,?,?,?,?,?,?,?)''', demands)
        connection.executemany('INSERT OR IGNORE INTO buyer_profiles (id,business_name,buyer_type,verification_status) VALUES (?,?,?,?)', [
            ('buyer-1001', 'Chennai Restaurant Collective', 'RESTAURANT', 'VERIFIED'),
            ('buyer-1002', 'Southstar Grocers', 'RETAILER', 'VERIFIED'),
            ('buyer-1003', 'Harvest Kitchen Co.', 'PROCESSOR', 'VERIFIED'),
            ('buyer-1004', 'The Green Table', 'RESTAURANT', 'VERIFIED'),
            ('buyer-1005', 'Daily Basket', 'RETAILER', 'VERIFIED'),
        ])
        orders = [
            ('CR-ORD-00231','CR-HRV-00041','farmer-01','Chennai Restaurant','RESTAURANT',10,'kg',350,'COMPLETED','PAID'),
            ('CR-ORD-00229','CR-HRV-00039','farmer-01','The Green Table','RESTAURANT',40,'units',1120,'DELIVERED','PAID'),
            ('CR-ORD-00224','CR-HRV-00037','farmer-02','Harvest Kitchen Co.','PROCESSOR',60,'kg',2100,'PROCESSING','PAID'),
            ('CR-ORD-00219','CR-HRV-00042','farmer-01','Southstar Grocers','RETAILER',120,'kg',5040,'PLACED','PENDING'),
            ('CR-ORD-00213','CR-HRV-00036','farmer-02','Daily Basket','RETAILER',80,'kg',4640,'COMPLETED','PAID'),
            ('CR-ORD-00208','CR-HRV-00041','farmer-01','Chennai Restaurant','RESTAURANT',25,'kg',875,'COMPLETED','PAID'),
        ]
        connection.executemany('''INSERT OR IGNORE INTO orders
          (id,harvest_id,farmer_id,buyer_name,buyer_type,quantity,unit,total_amount,status,payment_status)
          VALUES (?,?,?,?,?,?,?,?,?,?)''', orders)
        connection.executemany('INSERT OR IGNORE INTO deliveries (id,order_id,status,confirmed_at) VALUES (?,?,?,?)', [
            ('delivery-01','CR-ORD-00231','DELIVERED','2026-09-21T14:32:00'),
            ('delivery-02','CR-ORD-00229','DELIVERED','2026-09-20T12:00:00'),
            ('delivery-03','CR-ORD-00224','PENDING',None),
            ('delivery-04','CR-ORD-00219','PENDING',None),
            ('delivery-05','CR-ORD-00213','DELIVERED','2026-09-12T11:00:00'),
            ('delivery-06','CR-ORD-00208','DELIVERED','2026-09-09T16:00:00'),
        ])
        connection.execute("INSERT OR IGNORE INTO economic_credentials (id,farmer_id,credential_id,credential_hash) VALUES (?,?,?,?)", ('credential-01','farmer-01','CR-CRED-00001','local-demo-credential'))
        for batch in connection.execute('SELECT * FROM crop_batches ORDER BY created_at DESC').fetchall():
            evidence = {
                'batch_id': batch['id'],
                'crop_id': batch['harvest_id'],
                'farmer_id': batch['farmer_id'],
                'crop_type': batch['crop_name'],
                'quantity': batch['quantity'],
                'unit': batch['unit'],
                'harvest_date': batch['harvest_date'],
                'fingerprint': batch['fingerprint'],
            }
            metadata = {'network': 'devnet', 'status': 'PENDING', 'farmer_reference': batch['farmer_id'], 'verification': 'Awaiting blockchain confirmation'}
            evidence_hash = hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            metadata_hash = hashlib.sha256(json.dumps(metadata, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            ref_seed = f"{batch['id']}:{batch['farmer_id']}:{batch['crop_name']}"
            credential_id = f"CR-DC-{batch['id']}-{hashlib.sha256(ref_seed.encode()).hexdigest()[:10].upper()}"
            connection.execute('''INSERT OR IGNORE INTO crop_batch_credentials (id,batch_id,crop_id,farmer_id,farmer_identity_ref,crop_type,quantity,unit,harvest_id,harvest_date,harvest_location,evidence_hash,metadata_hash,status,network,metadata_json,created_at,updated_at)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
                credential_id,
                batch['id'],
                batch['harvest_id'],
                batch['farmer_id'],
                batch['farmer_id'],
                batch['crop_name'],
                float(batch['quantity']),
                batch['unit'],
                batch['harvest_id'],
                batch['harvest_date'],
                'Kanchipuram, Tamil Nadu',
                evidence_hash,
                metadata_hash,
                'PENDING',
                'devnet',
                json.dumps(metadata, sort_keys=True),
                batch['created_at'],
                batch['created_at']
            ))
        connection.commit()
    finally:
        connection.close()
