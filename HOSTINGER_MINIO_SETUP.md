# MinIO Setup on Hostinger (gistify.pro)

## Option 1: VPS/Cloud Hosting (Recommended)

### 1. SSH into your Hostinger VPS
```bash
ssh user@gistify.pro
```

### 2. Install MinIO
```bash
# Download MinIO
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
sudo mv minio /usr/local/bin/

# Create data directory
sudo mkdir -p /var/minio/data
sudo chown -R $USER:$USER /var/minio
```

### 3. Create MinIO service
```bash
sudo nano /etc/systemd/system/minio.service
```

Add this content:
```ini
[Unit]
Description=MinIO
Documentation=https://docs.min.io
After=network.target

[Service]
User=your-user
Group=your-user
ExecStart=/usr/local/bin/minio server /var/minio/data --address :9000 --console-address :9001
Restart=always
Environment="MINIO_ROOT_USER=admin"
Environment="MINIO_ROOT_PASSWORD=your-secure-password-here"

[Install]
WantedBy=multi-user.target
```

### 4. Start MinIO
```bash
sudo systemctl daemon-reload
sudo systemctl enable minio
sudo systemctl start minio
```

### 5. Configure Nginx Reverse Proxy
```bash
sudo nano /etc/nginx/sites-available/minio
```

Add:
```nginx
server {
    listen 80;
    server_name storage.gistify.pro;

    client_max_body_size 200M;

    location / {
        proxy_pass http://localhost:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for uploads
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/minio /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. Get SSL Certificate
```bash
sudo certbot --nginx -d storage.gistify.pro
```

### 7. Create Bucket
Access MinIO Console at: `https://storage.gistify.pro:9001`
- Login with: admin / your-secure-password
- Create bucket: `mp4totext`
- Set policy to "public" or create access policy

### 8. Update .env file
```env
STORAGE_ENDPOINT=storage.gistify.pro
STORAGE_ACCESS_KEY=admin
STORAGE_SECRET_KEY=your-secure-password-here
STORAGE_BUCKET=mp4totext
STORAGE_SECURE=true
```

---

## Option 2: Shared Hosting + External Storage

If you only have shared hosting, use one of these:

### A. Cloudflare R2 (S3-compatible, Free 10GB)
```env
STORAGE_ENDPOINT=your-account-id.r2.cloudflarestorage.com
STORAGE_ACCESS_KEY=your-r2-access-key
STORAGE_SECRET_KEY=your-r2-secret-key
STORAGE_BUCKET=mp4totext
STORAGE_SECURE=true
```

### B. Backblaze B2 (S3-compatible, $6/TB)
```env
STORAGE_ENDPOINT=s3.us-west-004.backblazeb2.com
STORAGE_ACCESS_KEY=your-b2-key-id
STORAGE_SECRET_KEY=your-b2-application-key
STORAGE_BUCKET=mp4totext
STORAGE_SECURE=true
```

### C. DigitalOcean Spaces (S3-compatible, $5/250GB)
```env
STORAGE_ENDPOINT=nyc3.digitaloceanspaces.com
STORAGE_ACCESS_KEY=your-spaces-key
STORAGE_SECRET_KEY=your-spaces-secret
STORAGE_BUCKET=mp4totext
STORAGE_SECURE=true
```

---

## Option 3: Simple File Server (No MinIO needed)

Create a simple upload endpoint on your Hostinger:

### 1. Create PHP upload script
`/public_html/storage/upload.php`:
```php
<?php
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$upload_dir = '/home/username/storage/';
if (!file_exists($upload_dir)) {
    mkdir($upload_dir, 0755, true);
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_FILES['file'])) {
    $file = $_FILES['file'];
    $filename = uniqid() . '_' . basename($file['name']);
    $target = $upload_dir . $filename;
    
    if (move_uploaded_file($file['tmp_name'], $target)) {
        $url = "https://gistify.pro/storage/" . $filename;
        echo json_encode(['success' => true, 'url' => $url]);
    } else {
        http_response_code(500);
        echo json_encode(['error' => 'Upload failed']);
    }
} else {
    http_response_code(400);
    echo json_encode(['error' => 'No file uploaded']);
}
?>
```

### 2. Update storage.py to use HTTP upload
Backend will upload via HTTP POST instead of MinIO.

---

## Recommended Solution

**For gistify.pro on Hostinger:**

1. **If VPS**: Use Option 1 (MinIO on VPS)
   - Full control
   - Fast uploads
   - Free

2. **If Shared Hosting**: Use Option 2A (Cloudflare R2)
   - Free 10GB
   - S3-compatible
   - Global CDN
   - Easy setup

3. **Quick & Simple**: Use Option 3 (PHP upload)
   - Works on any hosting
   - No additional services
   - Direct file serving

---

## Which hosting type do you have on Hostinger?
- [ ] VPS/Cloud
- [ ] Shared Hosting
- [ ] Not sure

Tell me and I'll configure the backend accordingly!
