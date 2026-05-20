from locust import HttpUser, task, between

class EcommerceUser(HttpUser):
    wait_time = between(2, 4)

    host = "https://insightful-renewal-production-0d32.up.railway.app"

    def on_start(self):
        response = self.client.post("/api/users/login", json={
            "email": "fizafarzand@gmail.com",
            "password": "karachi123"
        })

        self.token = None

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")   # ✅ FIXED

    def auth_headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    @task(4)
    def get_products(self):
        self.client.get("/api/products", headers=self.auth_headers())

    @task(3)
    def search_products(self):
        self.client.get("/api/products/search?q=camera", headers=self.auth_headers())

    @task(2)
    def get_user_profile(self):
        self.client.get("/api/users/me", headers=self.auth_headers())

    @task(2)
    def get_orders(self):
        self.client.get("/api/orders", headers=self.auth_headers())

    @task(1)
    def health_check(self):
        self.client.get("/api/health")