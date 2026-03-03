import random
import uuid
from locust import HttpUser, task, between

class WalletUser(HttpUser):
    # Simulate users clicking around every 0.1 to 0.5 seconds
    wait_time = between(0.1, 0.5)

    @task(3)
    def view_balances(self):
        user_id = random.randint(1, 2)  # Users 1 and 2 are seeded
        self.client.get(f"/v1/users/{user_id}/balances", name="/balances")

    @task(1)
    def topup(self):
        user_id = random.randint(1, 2)
        self.client.post("/v1/topup", json={
            "userId": user_id,
            "amount": random.randint(10, 50),
            "assetCode": "GOLD",
            "idempotencyKey": str(uuid.uuid4())
        }, name="/topup")

    @task(4)
    def spend(self):
        user_id = random.randint(1, 2)
        self.client.post("/v1/spend", json={
            "userId": user_id,
            "amount": random.randint(1, 10),
            "assetCode": "GOLD",
            "idempotencyKey": str(uuid.uuid4())
        }, name="/spend")
        
    @task(1)
    def check_transaction_history(self):
        user_id = random.randint(1, 2)
        self.client.get(f"/v1/users/{user_id}/transactions", name="/transactions")
