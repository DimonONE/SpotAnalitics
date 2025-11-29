import json
import os
from threading import Lock

DB_FILE = 'db.json'
db_lock = Lock()

def load_db():
    """Loads the database from the JSON file."""
    with db_lock:
        if not os.path.exists(DB_FILE):
            return {'users': {}, 'open_forecasts': {}, 'history': []}
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {'users': {}, 'open_forecasts': {}, 'history': []}

def save_db(data):
    """Saves the given data to the JSON database file."""
    with db_lock:
        with open(DB_FILE, 'w') as f:
            json.dump(data, f, indent=4, default=str)

def get_user_profile(user_id):
    """Retrieves a user's profile."""
    db = load_db()
    return db.get('users', {}).get(str(user_id))

def update_user_profile(user_id, settings):
    """Creates or updates a user's profile."""
    db = load_db()
    if 'users' not in db:
        db['users'] = {}
    db['users'][str(user_id)] = settings
    save_db(db)

def add_open_forecast(forecast):
    """Adds a new forecast to the open forecasts list."""
    db = load_db()
    symbol = forecast['symbol']
    if 'open_forecasts' not in db:
        db['open_forecasts'] = {}
    db['open_forecasts'][symbol] = forecast
    save_db(db)

def get_open_forecast(symbol):
    """
    Checks if there is an open forecast for a given symbol.
    Returns the forecast if it exists, otherwise None.
    """
    db = load_db()
    return db.get('open_forecasts', {}).get(symbol)

def close_forecast(symbol, outcome_data):
    """Moves a forecast from 'open' to 'history' and records the outcome."""
    db = load_db()
    open_forecasts = db.get('open_forecasts', {})
    
    if symbol in open_forecasts:
        forecast_to_close = open_forecasts.pop(symbol)
        
        # Add outcome data
        forecast_to_close.update(outcome_data)
        forecast_to_close['status'] = 'closed'
        
        if 'history' not in db:
            db['history'] = []
            
        db['history'].append(forecast_to_close)
        save_db(db)
        return forecast_to_close
    return None

def get_all_open_forecasts():
    """Returns a dictionary of all open forecasts."""
    db = load_db()
    return db.get('open_forecasts', {})

if __name__ == '__main__':
    # Example usage and testing of the database module
    print("--- Testing Database Module ---")
    
    # 1. Create a dummy user profile
    user_id_test = '12345'
    user_settings = {
        'username': 'testuser',
        'balance': 1000,
        'sl_method': 'atr',
        'atr_multiplier': 1.5
    }
    update_user_profile(user_id_test, user_settings)
    print(f"User {user_id_test} profile created.")
    
    # 2. Retrieve the profile
    profile = get_user_profile(user_id_test)
    print("Retrieved profile:", profile)
    assert profile['balance'] == 1000
    
    # 3. Add a dummy forecast
    dummy_forecast = {
        'forecast_id': 'dummy-uuid-1',
        'symbol': 'BTC/USDT',
        'direction': 'LONG',
        'entry_price': 65000
    }
    add_open_forecast(dummy_forecast)
    print("Added open forecast for BTC/USDT.")
    
    # 4. Check for the open forecast
    open_f = get_open_forecast('BTC/USDT')
    print("Retrieved open forecast:", open_f)
    assert open_f['entry_price'] == 65000
    
    # 5. Close the forecast
    outcome = {
        'outcome': 'HIT_TP1',
        'hit_price': 66500,
        'is_success': True
    }
    closed_f = close_forecast('BTC/USDT', outcome)
    print("Closed forecast:", closed_f)
    
    # 6. Verify it's in history and not in open
    db_state = load_db()
    assert 'BTC/USDT' not in db_state['open_forecasts']
    assert len(db_state['history']) == 1
    assert db_state['history'][0]['outcome'] == 'HIT_TP1'
    print("--- Database Module Test Passed ---")

    # Clean up the test db file
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print(f"Removed test database file: {DB_FILE}")
