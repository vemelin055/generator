#!/usr/bin/env python3
"""
Test połączenia z Google Sheets
"""

import os
import json
from datetime import datetime
from google_sheets_integration import GoogleSheetsIntegration

def test_google_sheets_connection():
    """Test połączenia z Google Sheets"""
    print("🧪 TEST POŁĄCZENIA Z GOOGLE SHEETS")
    print("=" * 50)
    
    # Sprawdzamy czy plik credentials istnieje
    if not os.path.exists("google_credentials.json"):
        print("❌ Brak pliku google_credentials.json")
        print("📋 Wykonaj kroki z GOOGLE_CLOUD_SETUP_GUIDE.md")
        return False
    
    # Sprawdzamy zawartość pliku
    try:
        with open("google_credentials.json", "r") as f:
            credentials = json.load(f)
        
        required_fields = ["type", "project_id", "private_key", "client_email"]
        missing_fields = [field for field in required_fields if field not in credentials]
        
        if missing_fields:
            print(f"❌ Brakujące pola w credentials: {missing_fields}")
            return False
        
        print("✅ Plik credentials jest poprawny")
        print(f"📧 Service Account: {credentials['client_email']}")
        print(f"🏗️ Project ID: {credentials['project_id']}")
        
    except json.JSONDecodeError:
        print("❌ Nieprawidłowy format JSON w credentials")
        return False
    except Exception as e:
        print(f"❌ Błąd odczytu credentials: {e}")
        return False
    
    # Testujemy połączenie
    print("\n🔗 Testowanie połączenia z Google Sheets...")
    
    try:
        integration = GoogleSheetsIntegration()
        
        if not integration.sheet:
            print("❌ Nie udało się połączyć z Google Sheets")
            print("💡 Sprawdź czy:")
            print("   - Service Account ma dostęp do arkusza")
            print("   - Arkusz jest udostępniony dla Service Account")
            print("   - Google Sheets API jest włączone")
            return False
        
        print("✅ Połączenie z Google Sheets udane!")
        
        # Testujemy zapis danych
        print("\n📊 Testowanie zapisu danych...")
        
        test_data = {
            "Test_Platform": {
                "platform": "Test Platform",
                "user_name": "Test User",
                "total_views": 100,
                "videos_count": 5,
                "videos": [
                    {
                        "title": "Test Video",
                        "views": 20,
                        "date": "2025-10-15T21:00:00Z"
                    }
                ]
            }
        }
        
        success = integration.save_to_sheets(test_data)
        
        if success:
            print("✅ Test zapisu udany!")
            print("📋 Sprawdź swój arkusz Google Sheets - powinien być nowy wiersz")
            return True
        else:
            print("❌ Test zapisu nieudany")
            return False
            
    except Exception as e:
        print(f"❌ Błąd testowania: {e}")
        return False

def main():
    """Główna funkcja"""
    success = test_google_sheets_connection()
    
    if success:
        print("\n🎉 WSZYSTKO DZIAŁA!")
        print("✅ Możesz teraz uruchomić: python official_api_extractor.py")
    else:
        print("\n❌ KONFIGURACJA WYMAGANA")
        print("📋 Wykonaj kroki z GOOGLE_CLOUD_SETUP_GUIDE.md")

if __name__ == "__main__":
    main()




