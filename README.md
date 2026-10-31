# reddot

Instagram reel + Auto-DM setup ("Comment LINK, link DM mein milega").

```
reel/     -> reel video generator (1080x1920, 15 sec)
autodm/   -> comment par automatic DM bhejne wala bot (official Instagram API)
```

## 1. Reel video

Ready video: `reel/output/reel.mp4`

Text, colours, keyword, brand name badalne ke liye `reel/reel_config.json` edit karein, phir:

```bash
pip install pillow        # ffmpeg bhi installed hona chahiye
python3 reel/make_reel.py
```

Video mein silent audio track hai. Post karte waqt Instagram ka trending audio lagayein.

## 2. Auto-DM setup

Jab koi aapke reel par keyword (jaise `LINK`) comment karega, bot use apne aap DM bhejega
aur comment par "Check your DM 📩" reply karega.

### Zaroori cheezein
- Instagram **Professional** account (Business ya Creator)
- [Meta for Developers](https://developers.facebook.com/) par ek App (type: Business), jisme **Instagram** product add ho
  ("API setup with Instagram login")
- Permissions: `instagram_business_basic`, `instagram_business_manage_comments`, `instagram_business_manage_messages`
- Bot ko host karne ki jagah jo public HTTPS URL de (Render, Railway, VPS, etc.)

### Steps
1. **Deploy**: `autodm/` folder ko host karein.
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app`
2. **Env variables** set karein (`autodm/.env.example` dekhein): `VERIFY_TOKEN`, `APP_SECRET`,
   `IG_ACCESS_TOKEN`, `IG_USER_ID`, `DM_KEYWORDS`, `DM_MESSAGE`, `PUBLIC_REPLY`.
   - Access token + IG user ID: App Dashboard -> Instagram -> API setup -> "Generate access token".
3. **Webhook** jodein: App Dashboard -> Instagram -> Webhooks
   - Callback URL: `https://<aapka-domain>/webhook`
   - Verify token: wahi jo `VERIFY_TOKEN` mein rakha
   - **comments** field ko subscribe karein
4. App ko **Live** mode mein daalein (Development mode mein sirf app roles wale users ke comments aate hain).
5. Test: apne reel par doosre account se `LINK` comment karein, DM aana chahiye.

### Dhyan rakhein
- Instagram ek comment par sirf **ek** private reply allow karta hai, aur woh comment ke 7 din ke andar.
- Ek hi account par zyada spam-type DMs se Instagram limit laga sakta hai. Message natural rakhein.
- `.env` / tokens kabhi GitHub par commit na karein.

### Test chalana
```bash
cd autodm && pip install -r requirements.txt pytest && python3 -m pytest -q
```
