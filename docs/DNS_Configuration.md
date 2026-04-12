# 域名与DNS配置

## 域名信息
| 域名 | 用途 | 注册商 | 注册人 | 到期时间 |
|------|------|--------|--------|----------|
| internship.example.com | 主域名（生产环境） | 阿里云 | 公司名称 | 2027-04-11 |
| test.internship.example.com | 测试环境 | 阿里云 | 公司名称 | 2027-04-11 |
| api.internship.example.com | API专用域名 | 阿里云 | 公司名称 | 2027-04-11 |

## DNS解析配置

### A记录（IPv4）
| 主机记录 | 记录类型 | 记录值 | TTL | 说明 |
|----------|----------|--------|-----|------|
| @ | A | 47.100.100.100 | 600 | 主域名解析到负载均衡器 |
| www | CNAME | internship.example.com | 600 | www域名别名 |
| test | A | 47.100.100.101 | 600 | 测试环境服务器 |
| api | A | 47.100.100.100 | 600 | API服务（与主域名共享） |
| * | A | 47.100.100.100 | 600 | 泛域名解析 |

### CNAME记录（CDN）
| 主机记录 | 记录类型 | 记录值 | TTL | 说明 |
|----------|----------|--------|-----|------|
| assets | CNAME | cdn.example.com | 300 | 静态资源CDN |
| img | CNAME | cdn.example.com | 300 | 图片资源CDN |

### MX记录（邮件）
| 主机记录 | 记录类型 | 记录值 | 优先级 | TTL |
|----------|----------|--------|--------|-----|
| @ | MX | mx1.email.example.com | 10 | 3600 |
| @ | MX | mx2.email.example.com | 20 | 3600 |

### TXT记录（验证与安全）
| 主机记录 | 记录类型 | 记录值 | TTL | 说明 |
|----------|----------|--------|-----|------|
| @ | TXT | "v=spf1 include:spf.email.example.com ~all" | 3600 | SPF记录 |
| _dmarc | TXT | "v=DMARC1; p=none; rua=mailto:dmarc@example.com" | 3600 | DMARC记录 |
| google-site-verification | TXT | "google-site-verification=xxxxxxxx" | 3600 | Google Search Console验证 |
| _github-challenge-xxx | TXT | "xxxxxxxx" | 3600 | GitHub Pages验证 |

## 负载均衡配置

### 阿里云SLB配置
| 配置项 | 值 | 说明 |
|--------|-----|------|
| 实例规格 | slb.s2.small | 性能共享型 |
| 带宽 | 5Mbps | 按流量计费 |
| 监听协议 | HTTPS (443) | 前端协议 |
| 后端协议 | HTTP (80) | 后端协议 |
| 健康检查路径 | /health | 健康检查端点 |
| 健康检查间隔 | 5秒 | |
| 健康检查超时 | 2秒 | |
| 健康检查阈值 | 连续成功2次标记健康 | |
| 不健康阈值 | 连续失败3次标记不健康 | |

### 后端服务器组
| 服务器IP | 端口 | 权重 | 说明 |
|----------|------|------|------|
| 47.100.100.102 | 80 | 100 | 应用服务器1 |
| 47.100.100.103 | 80 | 100 | 应用服务器2 |

## SSL证书配置

### 证书信息
| 证书名称 | 颁发机构 | 证书类型 | 有效期 | 支持的域名 |
|----------|----------|----------|--------|------------|
| internship.example.com | Let's Encrypt | DV SSL | 90天 | internship.example.com, www.internship.example.com |
| test.internship.example.com | Let's Encrypt | DV SSL | 90天 | test.internship.example.com |

### 证书自动化更新
```bash
#!/bin/bash
# /opt/certbot/renew_cert.sh
# 使用Certbot自动更新SSL证书

# 停止nginx
docker-compose -f /opt/internship-ai/docker-compose.prod.yml stop nginx

# 更新证书
certbot renew --quiet --deploy-hook "docker-compose -f /opt/internship-ai/docker-compose.prod.yml start nginx"

# 重启nginx
docker-compose -f /opt/internship-ai/docker-compose.prod.yml restart nginx
```

### 定时任务
```bash
# /etc/crontab
# 每周一凌晨3点检查证书更新
0 3 * * 1 root /opt/certbot/renew_cert.sh
```

## DNS健康检查

### 监控配置
```yaml
# Prometheus blackbox exporter配置
- job_name: 'dns_monitoring'
  metrics_path: /probe
  params:
    module: [dns_udp]
  static_configs:
    - targets:
      - internship.example.com
      - api.internship.example.com
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
- name: dns
  rules:
  - alert: DNSSECValidationFailure
    expr: probe_dns_rcode{job="dns_monitoring"} == 9
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "DNSSEC validation failed for {{ $labels.instance }}"
      
  - alert: DNSResolutionFailure
    expr: probe_success{job="dns_monitoring"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "DNS resolution failed for {{ $labels.instance }}"
```

## 域名备案信息

### ICP备案
| 项目 | 内容 |
|------|------|
| 备案号 | 沪ICP备202600001号 |
| 主办单位 | 上海某某科技有限公司 |
| 网站名称 | 学生求职AI助手 |
| 网站首页 | https://internship.example.com |
| 审核日期 | 2026-04-01 |
| 管局 | 上海市通信管理局 |

### 公安备案
| 项目 | 内容 |
|------|------|
| 公安备案号 | 沪公网安备31011502000001号 |
| 备案单位 | 上海某某科技有限公司 |
| 备案日期 | 2026-04-05 |
| 备案公安机关 | 上海市公安局网络警察总队 |

## DNS迁移方案

### 迁移前准备
1. **降低TTL**：提前24小时将TTL降低到300秒
2. **备份配置**：导出当前DNS配置
3. **通知用户**：发布维护公告

### 迁移步骤
```bash
# 1. 添加新DNS记录（保持旧记录）
# 2. 验证新记录解析正常
dig internship.example.com @8.8.8.8
nslookup internship.example.com 8.8.8.8

# 3. 修改NS记录指向新DNS服务商
# 4. 等待DNS传播（最长48小时）
# 5. 验证全球DNS解析
https://dnschecker.org/

# 6. 删除旧DNS记录
```

### 回滚计划
1. 恢复旧DNS配置
2. 修改NS记录回原服务商
3. 清除本地DNS缓存

## 性能优化

### DNS预取
```html
<!-- 在HTML头部添加DNS预取 -->
<link rel="dns-prefetch" href="//cdn.example.com">
<link rel="dns-prefetch" href="//api.internship.example.com">
```

### CDN集成
| CDN服务商 | 加速类型 | 配置状态 |
|-----------|----------|----------|
| 阿里云CDN | 全站加速 | 已配置 |
| Cloudflare | DNS代理 | 备用 |
| 腾讯云CDN | 图片加速 | 未配置 |

## 安全配置

### DNSSEC配置
```bash
# 启用DNSSEC
dnssec-keygen -a RSASHA256 -b 2048 -n ZONE internship.example.com
dnssec-signzone -A -3 $(head -c 1000 /dev/random | sha1sum | cut -b 1-16) -N INCREMENT -o internship.example.com -t internship.example.com.zone
```

### DDoS防护
| 防护类型 | 提供商 | 配置 |
|----------|--------|------|
| DNS防护 | 阿里云DNS | 已开启 |
| 流量清洗 | 阿里云DDoS高防 | 20Gbps防护 |
| Web应用防火墙 | 阿里云WAF | 已配置规则集 |

## 监控仪表板

### Grafana仪表板配置
```json
{
  "dashboard": {
    "title": "DNS监控仪表板",
    "panels": [
      {
        "title": "DNS解析时间",
        "targets": [{"expr": "probe_duration_seconds{job=\"dns_monitoring\"}"}]
      },
      {
        "title": "DNS解析成功率",
        "targets": [{"expr": "probe_success{job=\"dns_monitoring\"}"}]
      }
    ]
  }
}
```

## 联系人信息

### DNS服务商支持
| 服务商 | 联系方式 | 工作时间 |
|--------|----------|----------|
| 阿里云DNS | 95187 | 7x24小时 |
| DNSPod | 4009-188-188 | 工作日9:00-18:00 |

### 内部联系人
| 角色 | 姓名 | 电话 | 邮箱 |
|------|------|------|------|
| 运维负责人 | 张三 | 13800138000 | zhangsan@example.com |
| 网络工程师 | 李四 | 13900139000 | lisi@example.com |
| 安全工程师 | 王五 | 13700137000 | wangwu@example.com |

## 附录

### DNS记录验证命令
```bash
# 验证A记录
dig internship.example.com A +short
nslookup internship.example.com

# 验证CNAME记录
dig www.internship.example.com CNAME +short

# 验证MX记录
dig internship.example.com MX +short

# 验证TXT记录
dig internship.example.com TXT +short

# 验证DNS解析链
dig internship.example.com +trace

# 检查DNSSEC
dig internship.example.com +dnssec
```

### DNS性能测试
```bash
# 测试DNS解析时间
time dig internship.example.com

# 批量测试DNS服务器
for dns in 8.8.8.8 114.114.114.114 223.5.5.5; do
  echo "Testing $dns:"
  dig @$dns internship.example.com | grep "Query time"
done
```