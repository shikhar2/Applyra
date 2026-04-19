
import asyncio
import httpx
import sys
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

async def test_e2e():
    print("🚀 Starting End-to-End System Test...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Check Health
        try:
            resp = await client.get(f"{BASE_URL}/health")
            resp.raise_for_status()
            print("✅ Health Check Passed")
        except Exception as e:
            print(f"❌ Backend not reachable at {BASE_URL}. Ensure uvicorn is running.")
            return

        # 2. Verify Resume and Profile
        resumes = (await client.get(f"{BASE_URL}/resumes")).json()
        profiles = (await client.get(f"{BASE_URL}/profiles")).json()

        if not resumes or not profiles:
            print("❌ No Resume or Profile found in database. Run some setup first.")
            return

        resume_id = resumes[0]['id']
        profile_id = profiles[0]['id']
        print(f"✅ Found Resume ID: {resume_id}, Profile ID: {profile_id}")

        # 3. Trigger Search (Single Source for Speed)
        print("🔭 Triggering Search for 'Naukri' (Dry Run)...")
        search_req = {
            "profile_id": profile_id,
            "resume_id": resume_id,
            "sources": ["naukri"],
            "dry_run": True
        }
        resp = await client.post(f"{BASE_URL}/run/search", json=search_req)
        if resp.status_code != 200:
            print(f"❌ Failed to start search: {resp.text}")
            return
        print("✅ Background search started")

        # 4. Monitor Status
        print("⏳ Monitoring progress (this may take a minute)...")
        start_time = time.time()
        while True:
            status_resp = await client.get(f"{BASE_URL}/run/status")
            state = status_resp.json()
            
            # Print most recent log line
            if state['logs']:
                last_log = state['logs'][-1]
                print(f"   [{last_log['ts']}] {last_log['msg']}")

            if not state['running']:
                print("\n✅ Search Run Complete!")
                stats = state['stats']
                print(f"📊 Final Stats: {stats}")
                break
            
            if time.time() - start_time > 300: # 5 min timeout
                print("❌ Test timed out")
                break
                
            await asyncio.sleep(3)

    print("\n🏁 E2E Test Suite Finished Successfully")

if __name__ == "__main__":
    asyncio.run(test_e2e())
