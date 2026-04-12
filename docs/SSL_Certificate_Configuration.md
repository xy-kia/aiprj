# SSL证书配置

## 证书概览

### 证书信息表
| 证书名称 | 类型 | 颁发机构 | 加密算法 | 密钥长度 | 有效期 | 自动续期 |
|----------|------|----------|----------|----------|--------|----------|
| internship.example.com | DV SSL | Let's Encrypt | RSA | 2048位 | 90天 | 是 |
| test.internship.example.com | DV SSL | Let's Encrypt | RSA | 2048位 | 90天 | 是 |
| api.internship.example.com | DV SSL | Let's Encrypt | ECDSA | 256位 | 90天 | 是 |

### 支持的域名
| 证书 | 主域名 | SAN域名（附加域名） |
|------|--------|---------------------|
| 生产证书 | internship.example.com | www.internship.example.com, api.internship.example.com |
| 测试证书 | test.internship.example.com | - |

## 证书申请

### Let's Encrypt证书申请
```bash
#!/bin/bash
# 申请新证书脚本
# /opt/certbot/request_cert.sh

DOMAIN="internship.example.com"
EMAIL="admin@example.com"

# 使用Certbot申请证书
certbot certonly \
  --standalone \
  --non-interactive \
  --agree-tos \
  --email $EMAIL \
  --domains $DOMAIN,www.$DOMAIN,api.$DOMAIN \
  --preferred-challenges http \
  --http-01-port 80
```

### 证书文件位置
```
/etc/letsencrypt/live/internship.example.com/
├── cert.pem          # 证书文件
├── chain.pem         # 中间证书链
├── fullchain.pem     # 完整证书链（证书+中间证书）
└── privkey.pem       # 私钥文件
```

## Nginx配置

### SSL配置模板
```nginx
# /etc/nginx/conf.d/ssl.conf
ssl_certificate /etc/letsencrypt/live/internship.example.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/internship.example.com/privkey.pem;

# SSL协议配置
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;

# SSL密码套件
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;

# 会话缓存
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_session_tickets off;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;

# 安全头
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
```

### HTTP到HTTPS重定向
```nginx
server {
    listen 80;
    server_name internship.example.com www.internship.example.com;
    
    # 重定向到HTTPS
    return 301 https://$server_name$request_uri;
}
```

## 证书自动化续期

### Certbot自动续期配置
```bash
# 查看证书过期时间
certbot certificates

# 测试续期（不实际续期）
certbot renew --dry-run

# 实际续期
certbot renew

# 续期后重新加载Nginx
certbot renew --post-hook "systemctl reload nginx"
```

### 系统定时任务
```bash
# /etc/crontab
# 每天凌晨2点检查证书续期
0 2 * * * root /usr/bin/certbot renew --quiet --post-hook "systemctl reload nginx"

# 每周一凌晨3点测试续期
0 3 * * 1 root /usr/bin/certbot renew --dry-run
```

### Docker环境下的证书续期
```bash
#!/bin/bash
# /opt/internship-ai/scripts/renew_cert_docker.sh

# 停止nginx容器
docker-compose -f /opt/internship-ai/docker-compose.prod.yml stop nginx

# 运行certbot容器更新证书
docker run -it --rm \
  -v "/etc/letsencrypt:/etc/letsencrypt" \
  -v "/var/lib/letsencrypt:/var/lib/letsencrypt" \
  -p 80:80 \
  certbot/certbot renew

# 重启nginx容器
docker-compose -f /opt/internship-ai/docker-compose.prod.yml start nginx
```

## 证书监控

### 证书过期监控
```yaml
# Prometheus blackbox exporter配置
- job_name: 'ssl_expiry'
  metrics_path: /probe
  params:
    module: [http_2xx]
    target: [https://internship.example.com]
  static_configs:
    - targets:
      - https://internship.example.com
  relabel_configs:
    - source_labels: [__address__]
      target_label: __param_target
    - source_labels: [__param_target]
      target_label: instance
    - target_label: __address__
      replacement: blackbox-exporter:9115
```

### 告警规则
```yaml
# Prometheus告警规则
groups:
- name: ssl
  rules:
  - alert: SSLCertExpiringSoon
    expr: probe_ssl_earliest_cert_expiry{job="ssl_expiry"} - time() < 86400 * 30  # 30天
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "SSL证书即将过期 ({{ $value }}秒后)"
      description: "证书 {{ $labels.instance }} 将在30天内过期"
      
  - alert: SSLCertExpired
    expr: probe_ssl_earliest_cert_expiry{job="ssl_expiry"} - time() < 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "SSL证书已过期"
      description: "证书 {{ $labels.instance }} 已过期"
```

## 安全配置

### HSTS预加载
1. 访问 [HSTS Preload Submission](https://hstspreload.org/)
2. 提交域名：`internship.example.com`
3. 等待审核（通常需要几周）

### 证书透明度（CT）日志
```bash
# 检查证书是否在CT日志中
openssl x509 -in fullchain.pem -text | grep -A5 "CT Precertificate SCTs"

# 使用certbot提交到CT日志
certbot --force-renewal --preferred-challenges http -d internship.example.com \
  --deploy-hook "systemctl reload nginx" \
  --cert-name internship.example.com
```

### 密钥轮换策略
| 密钥类型 | 轮换周期 | 轮换方法 |
|----------|----------|----------|
| SSL私钥 | 每90天（与证书同步） | 证书续期时生成新密钥 |
| 中间证书 | 每年 | 手动更新 |
| 根证书 | 不轮换 | 信任库更新 |

## 多域名证书

### SAN证书配置
```bash
# 申请包含多个域名的证书
certbot certonly \
  --standalone \
  --non-interactive \
  --agree-tos \
  --email admin@example.com \
  --domains internship.example.com,www.internship.example.com,api.internship.example.com,test.internship.example.com
```

### 通配符证书
```bash
# 申请通配符证书（需要DNS验证）
certbot certonly \
  --manual \
  --preferred-challenges dns \
  --agree-tos \
  --email admin@example.com \
  --domains "*.example.com" \
  --server https://acme-v02.api.letsencrypt.org/directory
```

## 备份与恢复

### 证书备份
```bash
#!/bin/bash
# /opt/certbot/backup_certs.sh
BACKUP_DIR="/opt/backups/certificates"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 备份证书文件
tar czf $BACKUP_DIR/certs_$TIMESTAMP.tar.gz /etc/letsencrypt

# 备份Nginx配置
cp /etc/nginx/conf.d/ssl.conf $BACKUP_DIR/ssl.conf_$TIMESTAMP

# 保留最近30天的备份
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

### 证书恢复
```bash
#!/bin/bash
# /opt/certbot/restore_certs.sh
BACKUP_FILE="/opt/backups/certificates/certs_20260101_120000.tar.gz"

# 停止相关服务
systemctl stop nginx

# 恢复证书文件
tar xzf $BACKUP_FILE -C /

# 恢复后操作
chmod 600 /etc/letsencrypt/live/*/privkey.pem
chmod 644 /etc/letsencrypt/live/*/fullchain.pem

# 重启服务
systemctl start nginx
```

## 故障排除

### 常见问题

#### 1. 证书申请失败
```bash
# 检查80端口是否开放
netstat -tlnp | grep :80

# 检查域名解析
dig internship.example.com

# 查看Certbot日志
journalctl -u certbot
tail -f /var/log/letsencrypt/letsencrypt.log
```

#### 2. 证书续期失败
```bash
# 手动尝试续期
certbot renew --verbose

# 检查证书状态
certbot certificates

# 强制续期
certbot renew --force-renewal
```

#### 3. Nginx SSL配置错误
```bash
# 测试Nginx配置
nginx -t

# 查看错误日志
tail -f /var/log/nginx/error.log

# 检查证书文件权限
ls -la /etc/letsencrypt/live/internship.example.com/
```

### 调试命令
```bash
# 检查证书详细信息
openssl x509 -in /etc/letsencrypt/live/internship.example.com/fullchain.pem -text -noout

# 检查私钥
openssl rsa -in /etc/letsencrypt/live/internship.example.com/privkey.pem -check

# 测试SSL连接
openssl s_client -connect internship.example.com:443 -servername internship.example.com

# 使用SSL Labs测试
# 访问 https://www.ssllabs.com/ssltest/analyze.html?d=internship.example.com
```

## 性能优化

### SSL会话恢复
```nginx
# 启用会话票据
ssl_session_tickets on;
ssl_session_ticket_key /etc/nginx/ssl_ticket.key;

# 生成会话票据密钥
openssl rand 80 > /etc/nginx/ssl_ticket.key
chmod 600 /etc/nginx/ssl_ticket.key
```

### OCSP Stapling优化
```nginx
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/letsencrypt/live/internship.example.com/chain.pem;
```

### TLS 1.3 0-RTT
```nginx
# 启用0-RTT（注意安全风险）
ssl_early_data on;
```

## 合规与审计

### 合规要求
| 标准 | SSL/TLS要求 | 状态 |
|------|-------------|------|
| PCI DSS | TLS 1.2+，禁用弱密码 | 符合 |
| HIPAA | 加密传输，证书有效 | 符合 |
| GDPR | 数据传输加密 | 符合 |
| 等保2.0 | 国密算法支持 | 可选 |

### 审计检查清单
- [ ] 证书有效期 > 30天
- [ ] HSTS头已配置
- [ ] 禁用SSLv2、SSLv3、TLS 1.0、TLS 1.1
- [ ] 启用OCSP Stapling
- [ ] 证书透明度日志
- [ ] 定期密钥轮换记录
- [ ] 备份恢复测试记录

## 附录

### 证书链验证
```bash
# 验证证书链
openssl verify -CAfile /etc/letsencrypt/live/internship.example.com/chain.pem \
  /etc/letsencrypt/live/internship.example.com/cert.pem

# 检查证书链完整性
openssl s_client -connect internship.example.com:443 -showcerts
```

### 支持的浏览器列表
| 浏览器 | 最小版本 | 支持情况 |
|--------|----------|----------|
| Chrome | 50 | 支持 |
| Firefox | 52 | 支持 |
| Safari | 11 | 支持 |
| Edge | 17 | 支持 |
| IE | 不支持 | 已弃用 |

### 参考文档
- [Let's Encrypt文档](https://letsencrypt.org/docs/)
- [Mozilla SSL配置生成器](https://ssl-config.mozilla.org/)
- [SSL Labs测试工具](https://www.ssllabs.com/ssltest/)
- [Certbot用户指南](https://certbot.eff.org/docs/)