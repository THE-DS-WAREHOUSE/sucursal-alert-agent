import os
import requests
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def send_slack_alert(message: str, sucursal_name: str) -> bool:
    # Sends a single alert message to the configured Slack channel
    # Returns True if successful, False if failed
    if not SLACK_WEBHOOK_URL:
        raise ValueError("SLACK_WEBHOOK_URL not set in .env")

    payload = {
        "text": message,
        "username": "Sucursal Alert Bot",
        "icon_emoji": ":rotating_light:"
    }

    response = requests.post(
        SLACK_WEBHOOK_URL,
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 200:
        print(f"✅ Alert sent for {sucursal_name}")
        return True
    else:
        print(f"❌ Failed to send alert for {sucursal_name}: {response.status_code} {response.text}")
        return False

def send_all_alerts(flagged_sucursals: list) -> dict:
    # Sends one independent Slack message per flagged sucursal
    # Returns a summary of successful and failed sends
    results = {"sent": [], "failed": []}

    if not flagged_sucursals:
        print("✅ No sucursals in red zone today.")
        return results

    print(f"🚨 Sending alerts for {len(flagged_sucursals)} sucursals in red zone...")

    for sucursal in flagged_sucursals:
        success = send_slack_alert(
            message=sucursal["alert_message"],
            sucursal_name=sucursal["sucursal_name"]
        )
        if success:
            results["sent"].append(sucursal["sucursal_name"])
        else:
            results["failed"].append(sucursal["sucursal_name"])

    print(f"\n📊 Summary: {len(results['sent'])} sent, {len(results['failed'])} failed")
    return results