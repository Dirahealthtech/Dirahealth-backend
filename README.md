# 🏥 Dira Healthcare API

## 1. Project Name

**Dira Healthcare API** is a powerful and scalable backend API for an eCommerce platform specializing in **prosthetic limbs** and other **medical devices**.


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
DOMAIN=http://127.0.0.1:8000

# M-Pesa Configuration
MPESA_ENVIRONMENT=sandbox
MPESA_CONSUMER_KEY=your_consumer_key_from_daraja
MPESA_CONSUMER_SECRET=your_consumer_secret_from_daraja
MPESA_BUSINESS_SHORT_CODE=174379
MPESA_PASSKEY=bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919
MPESA_CALLBACK_URL=https://your-domain.com/api/v1/payments/mpesa/callback
MPESA_BUSINESS_NAME=Dira Healthcare
```

**Token Expiry Configuration:**
- `ACCESS_TOKEN_EXPIRY=604800` (1 week = 604,800 seconds)
- `REFRESH_TOKEN_EXPIRY=90` (90 days)
- `JTI_EXPIRY=604800` (1 week = 604,800 seconds)

> **Note**: The example above shows development-ready values. For production, generate secure random keys using the commands in section 4.3.

### 🔑 4.3 Generate SECRET_KEY and JWT_SECRET

Run this Python command in your terminal to generate secure keys:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"    # SECRET_KEY

python -c "import secrets; print(secrets.token_urlsafe(64))"    # JWT_SECRET
```

---

### 🔑 4.3 Generate SECRET_KEY and JWT_SECRET

Run this Python command in your terminal to generate secure keys:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"    # SECRET_KEY

python -c "import secrets; print(secrets.token_urlsafe(64))"    # JWT_SECRET
```

### 💳 4.4 M-Pesa Payment Integration Setup

The platform supports M-Pesa payments through Safaricom's Daraja API. Follow these steps to configure M-Pesa:

#### 4.4.1 Create Daraja Developer Account

1. Visit [Safaricom Daraja Portal](https://developer.safaricom.co.ke/)
2. Register a developer account
3. Login and create a new app
4. Select **"Lipa Na M-Pesa Sandbox"** API product
5. Get your **Consumer Key** and **Consumer Secret**

#### 4.4.2 M-Pesa Environment Variables

Add these M-Pesa configuration variables to your `.env` file:

```env
# M-Pesa Configuration (Sandbox for testing)
MPESA_ENVIRONMENT=sandbox
MPESA_CONSUMER_KEY=your_consumer_key_from_daraja
MPESA_CONSUMER_SECRET=your_consumer_secret_from_daraja
MPESA_BUSINESS_SHORT_CODE=174379
MPESA_PASSKEY=bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919
MPESA_CALLBACK_URL=https://your-domain.com/api/v1/payments/mpesa/callback
MPESA_BUSINESS_NAME=Dira Healthcare
```

**M-Pesa Configuration Explained:**

| Variable | Description | Sandbox Value | Production Value |
|----------|-------------|---------------|------------------|
| `MPESA_ENVIRONMENT` | API environment | `sandbox` | `production` |
| `MPESA_CONSUMER_KEY` | From Daraja app | Your app key | Your app key |
| `MPESA_CONSUMER_SECRET` | From Daraja app | Your app secret | Your app secret |
| `MPESA_BUSINESS_SHORT_CODE` | Paybill/Till number | `174379` | Your actual shortcode |
| `MPESA_PASSKEY` | STK Push passkey | Provided sandbox key | Your production key |
| `MPESA_CALLBACK_URL` | Webhook endpoint | Test URL | Your production URL |
| `MPESA_BUSINESS_NAME` | Business display name | Your business name | Your business name |

#### 4.4.3 Testing M-Pesa Integration

**Sandbox Testing:**
- Use test phone numbers: `254708374149` or `254711766949`
- Test amounts: Any value between 1-70000 KES
- No real money is processed

**Test STK Push Request:**
```json
{
  "phone_number": "254708374149",
  "amount": 10,
  "account_reference": "TEST001",
  "transaction_desc": "Test payment"
}
```

#### 4.4.4 Production Setup

⚠️ **Before switching to production:**

1. **Get Production Credentials:**
   - Apply for production access in Daraja portal
   - Get your actual business short code (paybill/till number)
   - Get production passkey from Safaricom

2. **Update Environment Variables:**
   ```env
   MPESA_ENVIRONMENT=production
   MPESA_BUSINESS_SHORT_CODE=your_actual_shortcode
   MPESA_PASSKEY=your_production_passkey
   MPESA_CALLBACK_URL=https://your-production-domain.com/api/v1/payments/mpesa/callback
   ```

3. **Deploy with Public Callback URL:**
   - Deploy your application to a public server
   - Ensure callback URL is accessible by Safaricom servers
   - Use HTTPS for production callback URLs

4. **Test with Small Amounts First:**
   - Start with small amounts (1-10 KES)
   - Verify callbacks are received
   - Test with real phone numbers

#### 4.4.5 M-Pesa API Endpoints

Once configured, these endpoints will be available:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/payments/mpesa/stk-push` | POST | Initiate STK Push payment |
| `/api/v1/payments/mpesa/order-payment` | POST | Pay for specific order |
| `/api/v1/payments/mpesa/status/{checkout_request_id}` | GET | Check payment status |
| `/api/v1/payments/mpesa/transactions/{transaction_id}` | GET | Get transaction details |
| `/api/v1/payments/mpesa/callback` | POST | M-Pesa callback endpoint |
| `/api/v1/payments/mpesa/config` | POST | Configure M-Pesa (Admin only) |

### 🔐 4.5 Authentication Token Configuration

The API uses JWT-based authentication with the following token lifespans:

| Token Type | Duration | Purpose |
|------------|----------|---------|
| **Access Token** | 1 week (604,800 seconds) | Main authentication for API requests |
| **Refresh Token** | 90 days | Long-term token renewal |
| **JTI Token** | 1 week (604,800 seconds) | Token tracking and blacklisting |

**Security Benefits:**
- ✅ Week-long access tokens reduce frequent re-authentication
- ✅ 90-day refresh tokens provide seamless user experience
- ✅ Suitable for healthcare applications requiring extended sessions
- ✅ Tokens can be revoked/blacklisted for security

**Custom Token Duration:**
To modify token lifespans, update these values in your `.env` file:
- **1 day**: `ACCESS_TOKEN_EXPIRY=86400`
- **1 month**: `ACCESS_TOKEN_EXPIRY=2592000`
- **6 months refresh**: `REFRESH_TOKEN_EXPIRY=180`

---

### 4.6 Running Database Migrations 🚀
Initialize Alembic (if not already initialized):
```bash
alembic init migrations
```
Generate and apply the initial migration:
```bash
alembic revision --autogenerate -m "initial migration"
alembic upgrade head
```

### 📦 4.7 Run the API

```bash
uvicorn app:app --reload
```

This will start the server at [http://127.0.0.1:8000](http://127.0.0.1:8000).

## 4.8 API docs - Swagger, redoc
Once the backend server is running, access the API documentation at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/api/v1/docs)
- **Redoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/api/v1/redoc)

---

### 🧠 4.9 Setting Up Redis (Online Version)

1. Sign up at a Redis hosting provider like [Redis Cloud](https://cloud.redis.io).
2. Create a new Redis database and copy the **connection URL** (format: `redis://default:<password>@<host>:<port>`).
3. Paste it into your `.env` as `REDIS_HOST`.

---

### 📧 4.10 Gmail App Password Setup

To send emails securely using Gmail:

1. Go to your [Google Account Security Settings](https://myaccount.google.com).
2. In the search bar shown in the home tab, type "App passwords"

   ![Screenshot from 2025-05-30 22-28-18](https://github.com/user-attachments/assets/02a442ff-9026-46ec-903b-2daf2b7c2453)

3. Click **App passwords** under "Security", you'll be prompted to enter your password.
4. Enter your app name in the form input shown below..

  ![Screenshot from 2025-05-30 22-30-40](https://github.com/user-attachments/assets/65036369-4185-41b7-918c-298fbaea9a43)

5. Copy the 16-character password, like the one shown in the image, and use it as `EMAIL_PASSWORD` in your `.env`.
   ![Screenshot from 2025-05-30 22-31-23](https://github.com/user-attachments/assets/e8ff4acc-c4ef-414f-9256-7f5b140a6dde)

6. You'll recieve an email notification for the generated app password.

---

### 🔄 4.11 Environment Switching Guide

#### Sandbox to Production Migration

When moving from development/testing to production:

1. **Update Environment Variables:**
   ```bash
   # Change in .env file
   MPESA_ENVIRONMENT=production
   MPESA_BUSINESS_SHORT_CODE=your_production_shortcode
   MPESA_PASSKEY=your_production_passkey
   MPESA_CALLBACK_URL=https://your-domain.com/api/v1/payments/mpesa/callback
   
   # Database (if moving to production database)
   DATABASE_URL=postgresql+asyncpg://user:password@production-host:5432/production_db
   
   # Security Keys (generate new ones for production)
   SECRET_KEY=your_production_secret_key
   JWT_SECRET=your_production_jwt_secret
   
   # Email (use production email credentials)
   MAIL_USERNAME=your-production-email@company.com
   MAIL_PASSWORD=your-production-app-password
   ```

2. **Update M-Pesa Configuration via API:**
   ```bash
   # Call admin endpoint to update M-Pesa config
   POST /api/v1/payments/mpesa/config
   ```

3. **Deploy Application:**
   - Deploy to production server (AWS, Google Cloud, Heroku, etc.)
   - Ensure callback URL is publicly accessible
   - Use HTTPS for all production URLs

#### Production Checklist

- [ ] Production Daraja credentials obtained
- [ ] Actual business shortcode and passkey configured
- [ ] Public callback URL accessible via HTTPS
- [ ] Production database configured
- [ ] New security keys generated
- [ ] Production email credentials set up
- [ ] SSL/TLS certificates configured
- [ ] Environment variables secured (not in version control)

### 🐛 4.12 Troubleshooting M-Pesa Integration

#### Common Issues and Solutions

**1. "Invalid CallBackURL" Error**
```
Error: Bad Request - Invalid CallBackURL
```
- **Cause**: Callback URL is not publicly accessible
- **Solution**: Use ngrok for local testing or deploy to public server
- **Sandbox**: Use dummy URL like `https://mydomain.com/callback` for testing

**2. OAuth Token Errors**
```
Error: Failed to get access token
```
- **Cause**: Invalid consumer key/secret
- **Solution**: Verify credentials from Daraja portal
- **Check**: Ensure no extra spaces in environment variables

**3. STK Push Not Received**
```
Success response but no STK push on phone
```
- **Sandbox**: Normal behavior, use test phone numbers
- **Production**: Verify phone number format (254XXXXXXXXX)
- **Check**: Ensure phone number is Safaricom/M-Pesa enabled

**4. Transaction Status Always "Failed"**
```
All transactions show as failed/cancelled
```
- **Sandbox**: Expected behavior, simulates various outcomes
- **Production**: Check actual transaction flow and callback processing

**5. Database Connection Errors**
```
Error: connection to database failed
```
- **Check**: DATABASE_URL format and credentials
- **Verify**: Database server is running
- **Ensure**: Database user has required permissions

#### Testing Commands

**Test OAuth Token:**
```bash
curl -X GET "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials" \
-H "Authorization: Basic base64(consumer_key:consumer_secret)"
```

**Test STK Push:**
```bash
# Use API documentation at /docs for interactive testing
# Or test via Postman with proper authentication
```

**Check Database Connection:**
```python
# Run in Python shell
import asyncpg
conn = await asyncpg.connect("your_database_url")
print("Database connected successfully!")
```

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
