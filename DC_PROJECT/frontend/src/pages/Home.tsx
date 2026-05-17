import { Link } from "react-router-dom";
import { useAuth } from "../store/AuthContext";

const featuredProducts = [
  {
    name: "Gaming Laptop",
    price: "$1200",
    image: "/images/laptop.jpg",
  },
  {
    name: "Wireless Headphones",
    price: "$180",
    image: "/images/headphone.jpg",
  },
  {
    name: "Smart Watch",
    price: "$250",
    image: "/images/watch.jpg",
  },
  {
    name: "Mechanical Keyboard",
    price: "$140",
    image: "/images/keyboard.jpg",
  },
  {
    name: "Smart Phone",
    price: "$950",
    image: "/images/phone.jpg",
  },
  {
    name: "Professional Camera",
    price: "$1800",
    image: "/images/camera.jpg",
  },

  {
    name: "Gaming Mouse",
    price: "$49.99",
    image: "/images/gaming-mouse.jpg",
  },


  {
    name: "Bluetooth Speaker",
    price: "$79.99",
    image: "/images/speaker.jpg",
  },

  {
    name: "Laptop Stand",
    price: "$34.99",
    image: "/images/laptop-stand.jpg",
  },

  {
    name: "Tablet",
    price: "$299.99",
    image: "/images/tablet.jpg",
  },

  {
    name: "Smart TV",
    price: "$699.99",
    image: "/images/smart-tv.jpg",
  }


];

export function Home() {
  const { user } = useAuth();

  return (
    <div className="space-y-20">
      <section className="grid items-center gap-10 rounded-3xl bg-gradient-to-r from-indigo-700 to-violet-700 px-8 py-16 text-white lg:grid-cols-2">
        <div>
          <h1 className="text-5xl font-extrabold leading-tight">
            Distributed E-Commerce Platform
          </h1>

          <p className="mt-6 text-lg text-indigo-100">
            A scalable microservices-based e-commerce system using API Gateway,
            RabbitMQ, Docker, Redis, MongoDB, and MySQL.
          </p>

          <div className="mt-8 flex flex-wrap gap-4">
            <Link
              to="/products"
              className="rounded-xl bg-white px-6 py-3 font-semibold text-indigo-700 shadow-lg transition hover:scale-105"
            >
              Shop Now
            </Link>

            {!user && (
              <Link
                to="/register"
                className="rounded-xl border border-white px-6 py-3 font-semibold transition hover:bg-white hover:text-indigo-700"
              >
                Create Account
              </Link>
            )}
          </div>
        </div>

        <div>
          <img
            src="/images/laptop.jpg"
            alt="Hero"
            className="rounded-3xl shadow-2xl"
          />
        </div>
      </section>

      <section>
        <div className="mb-8 text-center">
          <h2 className="text-4xl font-bold text-slate-900 dark:text-white">
            Featured Products
          </h2>

          <p className="mt-3 text-slate-600 dark:text-slate-400">
            Browse some of our latest products.
          </p>
        </div>

        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
          {featuredProducts.map((product) => (
            <div
              key={product.name}
              className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg transition hover:-translate-y-2 hover:shadow-2xl dark:border-slate-800 dark:bg-slate-900"
            >
              <img
                src={product.image}
                alt={product.name}
                className="h-64 w-full object-cover"
              />

              <div className="p-6">
                <h3 className="text-xl font-bold text-slate-900 dark:text-white">
                  {product.name}
                </h3>

                <p className="mt-2 text-lg font-semibold text-indigo-600">
                  {product.price}
                </p>

                <Link
                  to={user ? "/products" : "/login"}
                  className="mt-5 block w-full rounded-xl bg-indigo-600 px-4 py-3 text-center font-semibold text-white transition hover:bg-indigo-700"
                >
                  Add to Cart
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-10">
        <div className="text-center">
          <h2 className="text-4xl font-bold text-slate-900 dark:text-white">
            Services We Provide
          </h2>

          <p className="mt-3 text-slate-600 dark:text-slate-400">
            Our distributed architecture ensures scalability, reliability,
            performance, and efficient communication between services.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          <div className="rounded-2xl bg-white p-8 shadow-lg transition hover:-translate-y-2 hover:shadow-2xl dark:bg-slate-900">
            <h3 className="text-2xl font-bold text-indigo-600">
              API Gateway
            </h3>

            <p className="mt-4 text-slate-600 dark:text-slate-400">
              Centralized request routing, authentication, and communication
              management between distributed microservices.
            </p>
          </div>

          <div className="rounded-2xl bg-white p-8 shadow-lg transition hover:-translate-y-2 hover:shadow-2xl dark:bg-slate-900">
            <h3 className="text-2xl font-bold text-indigo-600">
              Async Payments
            </h3>

            <p className="mt-4 text-slate-600 dark:text-slate-400">
              RabbitMQ enables asynchronous payment processing for better
              scalability, reliability, and fault tolerance.
            </p>
          </div>

          <div className="rounded-2xl bg-white p-8 shadow-lg transition hover:-translate-y-2 hover:shadow-2xl dark:bg-slate-900">
            <h3 className="text-2xl font-bold text-indigo-600">
              Dockerized Services
            </h3>

            <p className="mt-4 text-slate-600 dark:text-slate-400">
              Independent containerized microservices allow flexible deployment,
              scalability, and efficient resource utilization.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}