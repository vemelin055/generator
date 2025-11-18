#!/usr/bin/env python3
"""
Test script for the fallback model functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_descriptions import DescriptionGenerator

def test_fallback_models():
    """Test the fallback model functionality"""
    print("🧪 Testing fallback models...")
    
    try:
        # Create a test instance with dry-run
        generator = DescriptionGenerator(
            sheet_id='1f0FkNY39YjnaVTTMfUBaN5JlyDK5ZCzM1MLW_qWnCDI',
            worksheet_name='КомТехАвто',
            dry_run=True,
            log_level='INFO',
            max_retries=2
        )
        
        print("✅ Generator created successfully")
        
        # Test the generation function directly
        print("🔧 Testing description generation...")
        result = generator._generate_description('TEST123', 'Test Part Name')
        
        print("✅ SUCCESS: Description generated")
        print(f"📝 Result: {result[:200]}..." if len(result) > 200 else result)
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_fallback_models()
    sys.exit(0 if success else 1)
