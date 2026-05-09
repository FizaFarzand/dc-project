import json
import random
from locust import HttpUser, task, between


class ECommerceUser(HttpUser):
    """Simulates an e-commerce user behavior"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    base_url = "http://localhost:8000/api"
    
    def on_start(self):
        """Called when a user starts"""
        self.user_id = random.randint(1, 10)
        self.token = None
        self.product_ids = ["prod_001", "prod_002", "prod_003"]
        self.register_user()
        self.login_user()
    
    def register_user(self):
        """Register a new user"""
        try:
            response = self.client.post(
                "/users/register",
                json={
                    "name": f"user_{self.user_id}_{random.randint(1000, 9999)}",
                    "email": f"user{self.user_id}@example.com",
                    "password": "password123"
                },
                name="register"
            )
            if response.status_code == 200:
                data = response.json()
                self.user_id = data.get("id", self.user_id)
        except Exception as e:
            print(f"Register error: {e}")
    
    def login_user(self):
        """Login to get token"""
        try:
            response = self.client.post(
                "/users/login",
                json={
                    "email": f"user{self.user_id}@example.com",
                    "password": "password123"
                },
                name="login"
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
        except Exception as e:
            print(f"Login error: {e}")
    
    @task(3)
    def list_products(self):
        """Fetch product list"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self.client.get("/products", headers=headers, name="list products")
    
    @task(2)
    def get_product_details(self):
        """Get details of a specific product"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        product_id = random.choice(self.product_ids)
        self.client.get(f"/products/{product_id}", headers=headers, name="get product")
    
    @task(2)
    def create_order(self):
        """Create a new order"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        product_id = random.choice(self.product_ids)
        quantity = random.randint(1, 3)
        
        response = self.client.post(
            "/orders",
            headers=headers,
            json={
                "product_id": product_id,
                "quantity": quantity
            },
            name="create order"
        )
    
    @task(1)
    def list_user_orders(self):
        """List orders for the user"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self.client.get(
            "/orders",
            headers=headers,
            name="list orders"
        )


class AdminUser(HttpUser):
    """Simulates admin user accessing products"""
    
    wait_time = between(2, 5)
    base_url = "http://localhost:8000/api"
    
    def on_start(self):
        """Login as admin"""
        self.token = None
        self.login_admin()
    
    def login_admin(self):
        """Login as admin user"""
        try:
            response = self.client.post(
                "/users/login",
                json={
                    "email": "admin@example.com",
                    "password": "admin123"
                },
                name="admin login"
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
        except Exception as e:
            print(f"Admin login error: {e}")
    
    @task(1)
    def view_products(self):
        """Admin viewing products"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self.client.get("/products", headers=headers, name="admin list products")
    
    @task(1)
    def create_product(self):
        """Admin creating a product"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        self.client.post(
            "/products",
            headers=headers,
            json={
                "name": f"Product_{random.randint(1, 1000)}",
                "description": "Test product",
                "price": random.uniform(10, 100),
                "stock": random.randint(10, 100)
            },
            name="create product"
        )
