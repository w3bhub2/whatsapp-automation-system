-- Create sent_numbers table
CREATE TABLE IF NOT EXISTS sent_numbers (
  phone TEXT PRIMARY KEY,
  business_name TEXT,
  email TEXT,
  first_sent_at TIMESTAMP,
  last_sent_at TIMESTAMP,
  last_replied_at TIMESTAMP,
  initial_sent_batch TEXT,
  followup_sent BOOLEAN DEFAULT FALSE,
  replied BOOLEAN DEFAULT FALSE,
  send_error TEXT
);

-- Create index on first_sent_at
CREATE INDEX IF NOT EXISTS idx_first_sent_at ON sent_numbers(first_sent_at);

-- Create batches table
CREATE TABLE IF NOT EXISTS batches (
  id TEXT PRIMARY KEY,
  created_at TIMESTAMP DEFAULT now(),
  csv_filename TEXT,
  processed_count INTEGER DEFAULT 0
);