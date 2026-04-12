# 网络与安全组策略配置

## 安全架构概述

### 网络拓扑
```
公网用户 → [Cloudflare/CDN] → [阿里云SLB] → [安全组] → [应用服务器] → [内部网络] → [数据库/缓存]
```

### 安全区域划分
| 区域 | 子网 | 用途 | 访问控制 |
|------|------|------|----------|
| DMZ区 | 10.0.1.0/24 | 负载均衡器、Nginx | 仅开放80/443端口 |
| 应用区 | 10.0.2.0/24 | 后端应用、前端应用 | 仅内部通信 |
| 数据区 | 10.0.3.0/24 | 数据库、缓存、存储 | 仅应用区访问 |
| 管理区 | 10.0.4.0/24 | 跳板机、监控、日志 | VPN访问 |

## 安全组配置

### 负载均衡器安全组（sg-lb）
| 规则方向 | 协议 | 端口 | 源IP | 描述 |
|----------|------|------|------|------|
| 入站 | TCP | 80 | 0.0.0.0/0 | HTTP访问 |
| 入站 | TCP | 443 | 0.0.0.0/0 | HTTPS访问 |
| 入站 | TCP | 22 | 管理IP段 | SSH管理 |
| 出站 | ALL | ALL | 0.0.0.0/0 | 允许所有出站 |

### 应用服务器安全组（sg-app）
| 规则方向 | 协议 | 端口 | 源IP | 描述 |
|----------|------|------|------|------|
| 入站 | TCP | 22 | 管理IP段 | SSH管理 |
| 入站 | TCP | 8000 | sg-lb | 后端API |
| 入站 | TCP | 80 | sg-lb | 前端服务 |
| 入站 | TCP | 9090 | sg-monitor | Prometheus监控 |
| 入站 | TCP | 9100 | sg-monitor | Node Exporter |
| 出站 | TCP | 3306 | sg-db | 数据库访问 |
| 出站 | TCP | 6379 | sg-cache | Redis访问 |
| 出站 | TCP | 443 | 0.0.0.0/0 | 外部API调用 |

### 数据库安全组（sg-db）
| 规则方向 | 协议 | 端口 | 源IP | 描述 |
|----------|------|------|------|------|
| 入站 | TCP | 3306 | sg-app | 应用访问 |
| 入站 | TCP | 3306 | 管理IP段 | 管理访问 |
| 入站 | TCP | 22 | 管理IP段 | SSH管理 |
| 出站 | ALL | ALL | 0.0.0.0/0 | 允许所有出站 |

### 缓存服务器安全组（sg-cache）
| 规则方向 | 协议 | 端口 | 源IP | 描述 |
|----------|------|------|------|------|
| 入站 | TCP | 6379 | sg-app | 应用访问 |
| 入站 | TCP | 22 | 管理IP段 | SSH管理 |
| 出站 | ALL | ALL | 0.0.0.0/0 | 允许所有出站 |

### 监控服务器安全组（sg-monitor）
| 规则方向 | 协议 | 端口 | 源IP | 描述 |
|----------|------|------|------|------|
| 入站 | TCP | 22 | 管理IP段 | SSH管理 |
| 入站 | TCP | 3000 | 管理IP段 | Grafana |
| 入站 | TCP | 9090 | 管理IP段 | Prometheus |
| 出站 | ALL | ALL | 0.0.0.0/0 | 允许所有出站 |

## 网络访问控制列表（NACL）

### DMZ区NACL（10.0.1.0/24）
| 规则号 | 类型 | 协议 | 端口 | 源 | 目标 | 动作 |
|--------|------|------|------|----|------|------|
| 100 | 入站 | TCP | 80 | 0.0.0.0/0 | 10.0.1.0/24 | 允许 |
| 101 | 入站 | TCP | 443 | 0.0.0.0/0 | 10.0.1.0/24 | 允许 |
| 102 | 入站 | TCP | 22 | 管理IP段 | 10.0.1.0/24 | 允许 |
| 200 | 出站 | TCP | 80 | 10.0.1.0/24 | 10.0.2.0/24 | 允许 |
| 201 | 出站 | TCP | 443 | 10.0.1.0/24 | 0.0.0.0/0 | 允许 |
| * | 入站/出站 | ALL | ALL | 0.0.0.0/0 | 0.0.0.0/0 | 拒绝 |

### 应用区NACL（10.0.2.0/24）
| 规则号 | 类型 | 协议 | 端口 | 源 | 目标 | 动作 |
|--------|------|------|------|----|------|------|
| 100 | 入站 | TCP | 80 | 10.0.1.0/24 | 10.0.2.0/24 | 允许 |
| 101 | 入站 | TCP | 8000 | 10.0.1.0/24 | 10.0.2.0/24 | 允许 |
| 102 | 入站 | TCP | 22 | 管理IP段 | 10.0.2.0/24 | 允许 |
| 103 | 入站 | TCP | 9090 | 10.0.4.0/24 | 10.0.2.0/24 | 允许 |
| 200 | 出站 | TCP | 3306 | 10.0.2.0/24 | 10.0.3.0/24 | 允许 |
| 201 | 出站 | TCP | 6379 | 10.0.2.0/24 | 10.0.3.0/24 | 允许 |
| 202 | 出站 | TCP | 443 | 10.0.2.0/24 | 0.0.0.0/0 | 允许 |
| * | 入站/出站 | ALL | ALL | 0.0.0.0/0 | 0.0.0.0/0 | 拒绝 |

## 端口使用说明

### 开放端口清单
| 端口 | 协议 | 服务 | 访问来源 | 用途 |
|------|------|------|----------|------|
| 22 | TCP | SSH | 管理IP段 | 服务器管理 |
| 80 | TCP | HTTP | 所有用户 | Web访问 |
| 443 | TCP | HTTPS | 所有用户 | 安全Web访问 |
| 8000 | TCP | FastAPI | 内部负载均衡器 | 后端API |
| 3306 | TCP | MySQL | 应用服务器 | 数据库访问 |
| 6379 | TCP | Redis | 应用服务器 | 缓存访问 |
| 9090 | TCP | Prometheus | 监控服务器 | 指标收集 |
| 9100 | TCP | Node Exporter | 监控服务器 | 节点监控 |
| 3000 | TCP | Grafana | 管理IP段 | 监控面板 |

### 禁止端口
| 端口 | 原因 | 替代方案 |
|------|------|----------|
| 21 | FTP明文传输 | SFTP (22端口) |
| 23 | Telnet不安全 | SSH (22端口) |
| 25 | SMTP可能被滥用 | 使用外部邮件服务 |
| 135-139 | NetBIOS漏洞 | 禁用 |
| 445 | SMB漏洞 | 禁用 |
| 1433 | SQL Server默认 | 不使用 |
| 3389 | RDP默认 | 使用跳板机 |

## DDoS防护配置

### 阿里云DDoS高防
| 配置项 | 值 | 说明 |
|--------|-----|------|
| 防护带宽 | 20Gbps | 基础防护 |
| 清洗阈值 | 500Mbps | 自动触发清洗 |
| 黑白名单 | 配置完成 | 已知IP管理 |
| CC防护 | 开启 | HTTP/HTTPS CC攻击防护 |

### Cloudflare防护
| 配置项 | 状态 | 说明 |
|--------|------|------|
| Under Attack模式 | 自动 | 遭受攻击时启用 |
| WAF规则 | 启用 | OWASP Top 10防护 |
| 速率限制 | 启用 | 100请求/分钟/IP |
| 机器人防护 | 启用 | 挑战可疑流量 |

## Web应用防火墙（WAF）配置

### 阿里云WAF规则集
| 规则组 | 规则数 | 防护类型 | 动作 |
|--------|--------|----------|------|
| 基础防护 | 15 | SQL注入、XSS、CSRF | 拦截 |
| 精准防护 | 5 | 自定义规则 | 拦截 |
| 白名单 | 10 | 可信IP | 放行 |
| 黑名单 | 20 | 恶意IP | 拦截 |

### 自定义WAF规则
```json
{
  "rules": [
    {
      "name": "阻止扫描工具",
      "condition": "User-Agent contains (nmap|sqlmap|wget|curl|python)",
      "action": "block"
    },
    {
      "name": "API速率限制",
      "condition": "URI startsWith '/api/' AND RequestCount > 100 per minute",
      "action": "captcha"
    },
    {
      "name": 阻止路径遍历",
      "condition": "URI contains '..' OR '~' OR '.git'",
      "action": "block"
    }
  ]
}
```

## VPN与堡垒机配置

### VPN接入
| VPN类型 | 客户端 | 认证方式 | 授权范围 |
|---------|--------|----------|----------|
| OpenVPN | 所有平台 | 证书+密码 | 管理区 |
| WireGuard | 所有平台 | 公钥加密 | 管理区 |
| IPSec | 网络设备 | 预共享密钥 | 站点到站点 |

### 跳板机（堡垒机）配置
| 配置项 | 值 | 说明 |
|--------|-----|------|
| 实例规格 | 2核4G | 足够支持10人并发 |
| 操作系统 | Ubuntu 22.04 | LTS版本 |
| 认证方式 | SSH密钥+OTP | 双因素认证 |
| 会话审计 | 开启 | 记录所有操作 |
| 命令限制 | 开启 | 危险命令拦截 |

## 流量监控与审计

### 网络流量监控
```yaml
# Suricata IDS配置
vars:
  address-groups:
    HOME_NET: "[10.0.0.0/16]"
    EXTERNAL_NET: "!$HOME_NET"
    
  port-groups:
    HTTP_PORTS: "[80,443,8000]"
    SQL_PORTS: "[3306]"

rules:
  - alert tcp $EXTERNAL_NET any -> $HOME_NET $SQL_PORTS
    msg: "SQL端口访问尝试";
    sid: 1000001;
```

### 访问日志分析
```bash
# Nginx日志分析脚本
#!/bin/bash
LOG_FILE="/var/log/nginx/access.log"

# 统计异常请求
awk '$9 >= 400 {print $1, $7, $9}' $LOG_FILE | sort | uniq -c | sort -rn

# 统计IP访问频率
awk '{print $1}' $LOG_FILE | sort | uniq -c | sort -rn

# 检测扫描行为
grep -E "(nmap|sqlmap|nikto|acunetix)" $LOG_FILE
```

## 应急响应流程

### 安全事件分类
| 级别 | 事件类型 | 响应时间 | 通知对象 |
|------|----------|----------|----------|
| P0 | 数据泄露、服务器入侵 | 15分钟内 | 安全团队、管理层 |
| P1 | DDoS攻击、WAF告警 | 30分钟内 | 运维团队、安全团队 |
| P2 | 端口扫描、异常登录 | 2小时内 | 值班人员 |
| P3 | 配置错误、策略调整 | 24小时内 | 相关责任人 |

### 应急响应步骤
1. **检测与确认**
   - 监控告警触发
   - 人工验证事件真实性
   - 确定影响范围

2. **遏制与隔离**
   - 封锁攻击源IP
   - 隔离受影响系统
   - 启用备用系统

3. **根除与恢复**
   - 清除后门/恶意软件
   - 修复安全漏洞
   - 恢复系统功能

4. **事后分析**
   - 事件根本原因分析
   - 安全策略优化
   - 审计报告编写

## 合规要求

### 网络安全法要求
| 要求 | 实施措施 | 检查周期 |
|------|----------|----------|
| 日志留存6个月 | 集中日志管理 | 每月 |
| 安全防护措施 | WAF、IDS、防火墙 | 每季度 |
| 应急预案 | 应急响应流程 | 每半年 |
| 安全检测评估 | 渗透测试 | 每年 |

### 等保2.0三级要求
| 控制项 | 要求 | 符合状态 |
|--------|------|----------|
| 访问控制 | 网络分区、最小权限 | 符合 |
| 安全审计 | 操作审计、日志分析 | 符合 |
| 入侵防范 | IDS/IPS、恶意代码防范 | 符合 |
| 集中管控 | 统一安全管理 | 符合 |

## 监控与告警

### 网络监控指标
| 指标 | 采集方式 | 告警阈值 |
|------|----------|----------|
| 带宽使用率 | SNMP/Zabbix | >80%持续5分钟 |
| 连接数 | NetFlow | >10000并发 |
| 丢包率 | Ping监控 | >5% |
| 延迟 | Ping监控 | >200ms |

### 安全告警规则
```yaml
# Prometheus告警规则
groups:
- name: network_security
  rules:
  - alert: PortScanDetected
    expr: increase(firewall_dropped_packets[5m]) > 1000
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "检测到端口扫描活动"
      
  - alert: DDoSAttack
    expr: rate(nginx_requests_total[5m]) > 1000
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "检测到DDoS攻击"
```

## 附录

### 安全组管理命令
```bash
# 查看安全组规则
iptables -L -n -v

# 添加安全组规则
iptables -A INPUT -p tcp --dport 80 -j ACCEPT

# 保存规则
iptables-save > /etc/iptables/rules.v4

# 阿里云CLI管理安全组
aliyun ecs AuthorizeSecurityGroup --SecurityGroupId sg-xxx --IpProtocol tcp --PortRange 80/80 --SourceCidrIp 0.0.0.0/0
```

### 网络诊断工具
```bash
# 检查端口开放
nc -zv internship.example.com 443
telnet internship.example.com 80

# 路由追踪
traceroute internship.example.com
mtr internship.example.com

# 网络性能测试
iperf3 -c internship.example.com -p 5201

# DNS解析测试
dig internship.example.com +trace
nslookup internship.example.com
```

### 安全扫描工具
```bash
# Nmap扫描
nmap -sS -sV -O internship.example.com

# 漏洞扫描
nikto -h internship.example.com

# SSL检测
sslscan internship.example.com
testssl.sh internship.example.com
```

### 联系人信息
| 角色 | 姓名 | 联系方式 | 职责 |
|------|------|----------|------|
| 网络安全负责人 | 张三 | 13800138000 | 安全策略制定 |
| 网络工程师 | 李四 | 13900139000 | 网络配置维护 |
| 安全工程师 | 王五 | 13700137000 | 安全事件响应 |
| 值班人员 | 赵六 | 13600136000 | 7x24小时监控 |