#!/usr/bin/env python3
import requests
import json
from datetime import datetime, timezone

def test_timestamps():
    try:
        response = requests.get('http://localhost:8000/api/history')
        data = response.json()
        
        print('=== FINAL TIMESTAMP VERIFICATION ===')
        print(f'Records found: {len(data)}')
        
        current_utc = datetime.now(timezone.utc)
        print(f'Current UTC time: {current_utc.isoformat()}')
        
        future_count = 0
        correct_count = 0
        
        for record in data[:5]:
            created_at = record.get('created_at', 'N/A')
            display = record.get('created_at_display', 'N/A')
            status = record.get('status', 'N/A')
            
            print(f'\nRecord: {record.get("id", "Unknown")[:8]}...')
            print(f'  Status: {status}')
            print(f'  UTC: {created_at}')
            print(f'  KST Display: {display}')
            
            try:
                if created_at != 'N/A':
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if dt > current_utc:
                        print('  Result: FUTURE TIME (ERROR)')
                        future_count += 1
                    else:
                        print('  Result: VALID TIME')
                        correct_count += 1
            except Exception as e:
                print(f'  Result: PARSE ERROR - {str(e)}')
        
        print(f'\n=== SUMMARY ===')
        print(f'Valid timestamps: {correct_count}')
        print(f'Future timestamps: {future_count}')
        if future_count == 0:
            print('✅ SUCCESS: All timestamps are now valid!')
        else:
            print(f'⚠️ WARNING: {future_count} timestamps still in the future')
            
        return future_count == 0
            
    except Exception as e:
        print(f'❌ Error: {str(e)}')
        return False

if __name__ == "__main__":
    test_timestamps()