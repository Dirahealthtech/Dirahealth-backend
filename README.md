# 🏥 Dira Healthcare API

## 1. Project Name

**Dira Healthcare API**
A powerful and scalable backend API for an eCommerce platform specializing in **prosthetic limbs** and other **medical devices**.


## 2. Overview

**Dira Healthcare** aims to connect users in need of prosthetic limbs with a wide catalog of customizable and affordable medical devices. The API serves as the backbone for:

* 🛒 Product browsing and purchasing
* 👤 User registration and authentication
* 📦 Order management
* 🧾 Invoicing and payment integration
* 🔒 Secure access with JWT tokens

This API is built using **FastAPI** with support for **asynchronous operations**, **JWT authentication**, and **email notifications** using **Gmail app passwords**.


## 3. User Instructions

Here’s how users interact with the platform:

* **Sign up / Login** to the platform using email and password
* **Browse products** such as prosthetic limbs, medical accessories, etc.
* **Add to cart** and **place orders**
* **Receive confirmation emails** for registration and purchases
* **Track order status** from the user dashboard

All interactions are handled through clean REST endpoints, protected using **JWT-based authentication**.


## 4. Developer Instructions

To get started with development:

### 🧰 4.1 Clone and Setup

```bash
git clone https://github.com/Techloom25/Dira_healthcare_backend.git

cd Dira_healthcare_api

python -m venv venv     # use "python3 -m venv .venv" if this does not work
source venv/bin/activate  # On Windows: venv\Scripts\activate

# install dependencies
pip install -r requirements.txt
```

### 🔐 4.2 Environment Variables (`.env`)

Create a `.env` file at the root level and include the following:

```env
DATABASE_URL=sqlite+aiosqlite:///./db.sqlite3   # development db
SECRET_KEY=<your-secret_key>
JWT_ALGORITHM=HS256
JWT_SECRET=<your-jwt-secret>
ACCESS_TOKEN_EXPIRY=3600
REFRESH_TOKEN_EXPIRY=1
JTI_EXPIRY=3600
REDIS_HOST=<your-redis-host>    # if you're using redis cloud
REDIS_PORT=<your-redis-port>    # if you are using redis locally
REDIS_PASSWORD=<your-redis-password>    # if you are using redis locally
MAIL_USERNAME=<mail-username>
MAIL_PASSWORD=<16-digit-app-password>
MAIL_FROM=<your-email-address>
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com
MAIL_FROM_NAME=Dira Healthcare
MAIL_STARTTLS=True
MAIL_SSL_TLS=False
USE_CREDENTIALS=True
VALIDATE_CERTS=True
DOMAIN=http://127.0.0.1:8000    # change to production domain when deployed
```

### 🔑 4.3 Generate SECRET_KEY and JWT_SECRET

Run this Python command in your terminal to generate secure keys:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"    # SECRET_KEY

python -c "import secrets; print(secrets.token_urlsafe(64))"    # JWT_SECRET
```

---

### 4.4 Running Database Migrations 🚀
Initialize Alembic (if not already initialized):
```bash
alembic init migrations
```
Apply the migrations:
```bash
alembic upgrade head
```

### 📦 4.5 Run the API

```bash
uvicorn app:app --reload
```

This will start the server at [http://127.0.0.1:8000](http://127.0.0.1:8000).

## 4.6 API docs - Swagger, redoc
Once the backend server is running, access the API documentation at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/api/v1/docs)
- **Redoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/api/v1/redoc)

---

### 🧠 4.7 Setting Up Redis (Online Version)

1. Sign up at a Redis hosting provider like [Redis Cloud](https://cloud.redis.io).
2. Create a new Redis database and copy the **connection URL** (format: `redis://default:<password>@<host>:<port>`).
3. Paste it into your `.env` as `REDIS_HOST`.

---

### 📧 4.8 Gmail App Password Setup

To send emails securely using Gmail:

1. Go to your [Google Account Security Settings](https://myaccount.google.com).
2. In the search bar shown in the home tab, type "App passwords"
3. Click **App passwords** under "Security", you'll be prompted to enter your password.
4. Enter your app name in the form input shown below..
5. Copy the 16-character password and use it as `EMAIL_PASSWORD` in your `.env`.

---

## 5. Known Issues / Bugs 🐛

* Caching may not work correctly if Redis credentials are invalid or expired.
* Gmail rate limits may apply for frequent email notifications.

If you encounter any issues, feel free to open an issue on GitHub!

---

## 6. Contribution 🤝

We welcome contributions! Here's how:

1. Fork the repository
2. Create a new branch (`git checkout -b <your-branch-name>`)
3. Make your changes
4. Commit and push (`git commit -m "Add new feature"`)
5. Open a pull request


## 7. Testing 🧪
You can test the API using [Postman](https://www.postman.com), curl or the FastAPI interactive docs:

### 7.1 Installing Postman

**Postman** is a popular API testing tool. You can install it by following these steps:

Windows/macOS/Linux: Download the latest version from the official [Postman](https://www.postman.com) website.

Follow the installation prompts to complete the setup.

### 7.2 Installing curl 🌍

`curl` is a command-line tool for making API requests. It comes pre-installed on most Linux/macOS systems. If it's missing, install it using:

**Windows**: Download and install curl from the [official website](https://curl.se/) or use Git Bash (comes with curl pre-installed).

**Linux (Debian/Ubuntu)**:

```bash
sudo apt update && sudo apt install curl
```

**macOS**: curl is pre-installed, but you can update it using Homebrew:
```bash
brew install curl
```


Happy coding 🎉
