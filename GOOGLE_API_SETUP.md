# 🔑 Google API Setup Guide for Zonemation

## 📊 Current Status

**You're currently using:** Free Google Web Speech API (unofficial)
- ❌ No API key needed
- ❌ Limited to ~50 requests/day
- ❌ No usage tracking
- ❌ Not for production

## 🎯 What You Need: Google Cloud Speech-to-Text API

### **Option 1: API Key (Simple)** ⭐ Recommended to Start
Quick setup, good for testing, easy billing

### **Option 2: Service Account (Secure)**
More secure, better for production, complex setup

---

## 📋 Step-by-Step Setup

### **Step 1: Create Google Cloud Account**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Sign up with Google account
3. Add billing (required for API)
   - You get **$300 free credits** for 90 days
   - Then **60 minutes free** per month
   - After that: **$0.006 per 15 seconds** (~$0.024/minute)

### **Step 2: Create Project**
1. Click "Create Project"
2. Name: `zonemation-darija`
3. Note the Project ID

### **Step 3: Enable Speech-to-Text API**
1. Go to "APIs & Services" → "Library"
2. Search: "Cloud Speech-to-Text API"
3. Click and Enable

### **Step 4: Create API Credentials**

#### **For API Key (Simple):**
1. Go to "APIs & Services" → "Credentials"
2. Click "+ CREATE CREDENTIALS" → "API Key"
3. Copy the key immediately!
4. Click "Restrict Key":
   - **API restrictions**: Cloud Speech-to-Text API only
   - **Application restrictions**: HTTP referrers
   - Add: `https://*.up.railway.app/*`
5. Save

#### **For Service Account (Secure):**
1. Go to "APIs & Services" → "Credentials"
2. Click "+ CREATE CREDENTIALS" → "Service Account"
3. Name: `darija-transcription`
4. Grant role: "Cloud Speech Client"
5. Create JSON key → Download file
6. Upload to Railway as environment variable

### **Step 5: Add to Railway**

Add these environment variables:

```bash
# Option 1: API Key
GOOGLE_API_KEY=AIza...your-key-here

# Option 2: Service Account
GOOGLE_CREDENTIALS_PATH=/app/credentials.json
# Or base64 encode the JSON and add as:
GOOGLE_CREDENTIALS_JSON=base64-encoded-json-here
```

---

## 💰 **Cost Calculation**

### **Google Cloud Pricing:**
- **Free Tier**: 60 minutes/month
- **After Free**: $0.006 per 15 seconds

### **Your Costs Example:**
| Usage | Monthly Cost |
|-------|-------------|
| 100 transcriptions × 30 sec | Free (50 min) |
| 500 transcriptions × 30 sec | Free + $3.60 |
| 1000 transcriptions × 30 sec | $10.80 |
| 5000 transcriptions × 30 sec | $54.00 |

### **Cost Control:**
1. Set budget alerts in Google Cloud
2. Use Zonemation tokens to track per-client usage
3. Pass costs to clients: charge $0.01-0.02 per transcription

---

## 🔄 **Migration Plan**

### **Phase 1: Test (Current)**
- Using free tier
- Good for development

### **Phase 2: Add API Key**
1. Create Google API key
2. Add to Railway environment
3. Update code to use new service
4. Test with small volume

### **Phase 3: Production**
1. Switch to service account
2. Implement usage tracking
3. Set up billing for clients
4. Monitor costs

---

## 📊 **Usage Tracking Strategy**

### **Your Zonemation Tokens Track:**
```python
# Per token/client:
- Number of requests
- Total audio duration
- Estimated Google API cost
- Your markup/profit
```

### **Billing Your Clients:**
```
Google Cost: $0.006 per 15 sec
Your Price:  $0.015 per 15 sec (2.5x markup)
Profit:      $0.009 per 15 sec
```

### **Monthly Revenue Example:**
- 10 clients × 500 requests × 30 sec = $45 profit
- 50 clients × 500 requests × 30 sec = $225 profit
- 100 clients × 500 requests × 30 sec = $450 profit

---

## 🚨 **Important Notes**

1. **Current Code Limitation:**
   - The app uses `speech_recognition` library
   - It doesn't use official Google Cloud API yet
   - You need to update the code to use `google_transcription.py`

2. **To Use Paid API:**
   ```python
   # In app_production.py, replace:
   r.recognize_google(audio, language="ar-MA")
   
   # With:
   from google_transcription import GoogleTranscriptionService
   service = GoogleTranscriptionService(api_key=GOOGLE_API_KEY)
   result = service.transcribe_audio(audio_file, language="ar-MA")
   ```

3. **Monitor Usage:**
   - Set up billing alerts at $10, $50, $100
   - Track usage per Zonemation token
   - Review Google Cloud console weekly

---

## ✅ **Action Items**

1. **Today:**
   - [ ] Create Google Cloud account
   - [ ] Get $300 free credits
   - [ ] Enable Speech-to-Text API

2. **This Week:**
   - [ ] Create API key
   - [ ] Add to Railway environment
   - [ ] Test with low volume

3. **Next Month:**
   - [ ] Implement usage tracking
   - [ ] Set client pricing
   - [ ] Switch to service account

---

## 📞 **Need Help?**

- Google Cloud Support: console.cloud.google.com/support
- Pricing Calculator: cloud.google.com/products/calculator
- API Documentation: cloud.google.com/speech-to-text/docs