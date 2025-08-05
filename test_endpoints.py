#!/usr/bin/env python3
"""
Test session validation across different Cognos endpoints
"""

import requests

def test_session_endpoints():
    # Test the session with different endpoints
    session_key = 'CAM MTsxMDE6YmU0ZjJiOWItNjY1Ni1hYmE2LTFmM2EtYWFmMWZiYjUzNTdlOjA5NzEwNDc2OTc7MDszOzA7'
    cognos_url = 'http://20.244.32.126:9300/api/v1'

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'IBM-BA-Authorization': session_key
    }

    endpoints = ['/content', '/modules', '/capabilities', '/session', '/datasources']

    print('Testing session with different endpoints:')
    print(f'Session key: {session_key[:30]}...')
    print()

    for endpoint in endpoints:
        try:
            url = f'{cognos_url}{endpoint}'
            response = requests.get(url, headers=headers, timeout=10)
            
            print(f'{endpoint:15} - Status: {response.status_code}')
            
            if response.status_code != 200:
                print(f'                Response: {response.text[:100]}...')
            else:
                # Show some response data for successful calls
                try:
                    data = response.json()
                    if endpoint == '/content' and 'content' in data:
                        print(f'                Items: {len(data.get("content", []))} content items')
                    elif endpoint == '/modules' and 'modules' in data:
                        print(f'                Items: {len(data.get("modules", []))} modules')
                    elif endpoint == '/capabilities':
                        print(f'                Capabilities available')
                    elif endpoint == '/session':
                        print(f'                Anonymous: {data.get("isAnonymous", "unknown")}')
                    elif endpoint == '/datasources':
                        print(f'                Data sources available')
                except:
                    print(f'                Response length: {len(response.text)} chars')
            
        except Exception as e:
            print(f'{endpoint:15} - Error: {str(e)}')
        
        print()

if __name__ == "__main__":
    test_session_endpoints()