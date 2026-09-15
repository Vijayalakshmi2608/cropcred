from pathlib import Path
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
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  harvest_id TEXT NOT NULL REFERENCES harvests(id),
  farmer_id TEXT NOT NULL REFERENCES farmers(id),
  buyer_name TEXT NOT NULL,
  buyer_type TEXT NOT NULL,
  quantity REAL NOT NULL CHECK(quantity > 0),
  unit TEXT NOT NULL,
  total_amount REAL NOT NULL CHECK(total_amount >= 0),
  status TEXT NOT NULL CHECK(status IN ('PLACED','PROCESSING','OUT_FOR_DELIVERY','DELIVERED','COMPLETED','CANCELLED')),
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
'''


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    return connection


def init_db():
    connection = get_connection()
    connection.executescript(SCHEMA)
    connection.commit()
    connection.close()


def seed_db():
    connection = get_connection()
    if connection.execute('SELECT COUNT(*) FROM farmers').fetchone()[0] > 0:
        connection.close()
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
    demands = [
        ('DEM-1001','Chennai Restaurant Collective','RESTAURANT','Tomatoes',500,'kg',32,38,'Chennai','Weekly','3 days remaining'),
        ('DEM-1002','Southstar Grocers','RETAILER','Bananas',1000,'kg',38,44,'Bengaluru','Weekly','Weekly requirement'),
        ('DEM-1003','Harvest Kitchen Co.','PROCESSOR','Tomatoes',2000,'kg',29,34,'Coimbatore','Monthly','8 days remaining'),
        ('DEM-1004','The Green Table','RESTAURANT','Coconut',300,'units',25,30,'Pondicherry','Weekly','5 days remaining'),
        ('DEM-1005','Daily Basket','RETAILER','Onions',750,'kg',24,28,'Chennai','Weekly','12 days remaining'),
    ]
    connection.executemany('''INSERT INTO demands
      (id,buyer_name,buyer_type,crop,quantity,unit,price_min,price_max,location,frequency,deadline)
      VALUES (?,?,?,?,?,?,?,?,?,?,?)''', demands)
    orders = [
        ('CR-ORD-00231','CR-HRV-00041','farmer-01','Chennai Restaurant','RESTAURANT',10,'kg',350,'COMPLETED','PAID'),
        ('CR-ORD-00229','CR-HRV-00039','farmer-01','The Green Table','RESTAURANT',40,'units',1120,'DELIVERED','PAID'),
        ('CR-ORD-00224','CR-HRV-00037','farmer-02','Harvest Kitchen Co.','PROCESSOR',60,'kg',2100,'PROCESSING','PAID'),
        ('CR-ORD-00219','CR-HRV-00042','farmer-01','Southstar Grocers','RETAILER',120,'kg',5040,'PLACED','PENDING'),
        ('CR-ORD-00213','CR-HRV-00036','farmer-02','Daily Basket','RETAILER',80,'kg',4640,'COMPLETED','PAID'),
        ('CR-ORD-00208','CR-HRV-00041','farmer-01','Chennai Restaurant','RESTAURANT',25,'kg',875,'COMPLETED','PAID'),
    ]
    connection.executemany('''INSERT INTO orders
      (id,harvest_id,farmer_id,buyer_name,buyer_type,quantity,unit,total_amount,status,payment_status)
      VALUES (?,?,?,?,?,?,?,?,?,?)''', orders)
    connection.executemany('INSERT INTO deliveries (id,order_id,status,confirmed_at) VALUES (?,?,?,?)', [
        ('delivery-01','CR-ORD-00231','DELIVERED','2026-09-21T14:32:00'),
        ('delivery-02','CR-ORD-00229','DELIVERED','2026-09-20T12:00:00'),
        ('delivery-03','CR-ORD-00224','PENDING',None),
        ('delivery-04','CR-ORD-00219','PENDING',None),
        ('delivery-05','CR-ORD-00213','DELIVERED','2026-09-12T11:00:00'),
        ('delivery-06','CR-ORD-00208','DELIVERED','2026-09-09T16:00:00'),
    ])
    connection.execute("INSERT INTO economic_credentials (id,farmer_id,credential_id,credential_hash) VALUES (?,?,?,?)", ('credential-01','farmer-01','CR-CRED-00001','local-demo-credential'))
    connection.commit()
    connection.close()
