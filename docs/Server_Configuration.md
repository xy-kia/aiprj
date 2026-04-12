# 生产环境服务器配置

## 服务器规格
| 服务器角色 | 数量 | 配置要求 | 云服务商 | 区域 |
|------------|------|----------|----------|------|
| 应用服务器 | 2 | 4核8G，100G SSD，5M带宽 | 阿里云 | 华东2（上海） |
| 数据库服务器 | 1 | 4核8G，200G SSD，3M带宽 | 阿里云 | 华东2（上海） |
| 缓存服务器 | 1 | 2核4G，50G SSD，3M带宽 | 阿里云 | 华东2（上海） |

## 系统配置

### 操作系统
- **发行版**：Ubuntu 22.04 LTS
- **内核版本**：5.15.x
- **时区**：Asia/Shanghai

### 基础软件包
```bash
# 更新系统
apt-get update && apt-get upgrade -y

# 安装基础工具
apt-get install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    net-tools \
    ntp \
    ufw \
    fail2ban \
    logrotate \
    supervisor \
    docker.io \
    docker-compose
```

### 用户与权限
```bash
# 创建部署用户
useradd -m -s /bin/bash deploy
usermod -aG docker deploy

# 配置SSH密钥认证
mkdir -p /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC..." > /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh
```

## Docker配置

### Docker Daemon配置
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "iptables": false,
  "live-restore": true
}
```

### Docker Compose安装
```bash
# 安装最新版本
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep tag_name | cut -d'"' -f4)
curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

## 目录结构
```
/opt/internship-ai/
├── docker-compose.prod.yml
├── .env.prod
├── nginx/
│   ├── nginx.conf
│   ├── conf.d/
│   └── ssl/
├── scripts/
│   ├── backup.sh
│   ├── deploy.sh
│   └── monitor.sh
├── logs/
│   ├── nginx/
│   ├── backend/
│   └── database/
└── data/
    ├── mysql/
    └── redis/
```

## 系统优化

### 内核参数调整
```bash
# /etc/sysctl.conf
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 300
vm.swappiness = 10
vm.overcommit_memory = 1
```

### 文件描述符限制
```bash
# /etc/security/limits.conf
* soft nofile 65535
* hard nofile 65535
* soft nproc 65535
* hard nproc 65535
```

### 时区同步
```bash
# 安装chrony
apt-get install -y chrony
systemctl enable chrony
systemctl start chrony

# 验证时间同步
chronyc sources -v
```

## 监控配置

### 基础监控
```bash
# 安装node_exporter
wget https://github.com/prometheus/node_exporter/releases/download/v1.6.0/node_exporter-1.6.0.linux-amd64.tar.gz
tar xzf node_exporter-*.tar.gz
cp node_exporter-*/node_exporter /usr/local/bin/
useradd -rs /bin/false node_exporter

# 创建systemd服务
cat > /etc/systemd/system/node_exporter.service << EOF
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable node_exporter
systemctl start node_exporter
```

## 安全配置

### SSH加固
```bash
# /etc/ssh/sshd_config
Port 2222
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AllowUsers deploy
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
```

### 防火墙配置
```bash
# 启用UFW
ufw default deny incoming
ufw default allow outgoing

# 开放必要端口
ufw allow 2222/tcp  # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 8000/tcp  # Backend API (internal)

# 启用防火墙
ufw enable
ufw status verbose
```

### Fail2ban配置
```bash
# /etc/fail2ban/jail.local
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = 2222
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
```

## 备份配置

### 自动备份脚本
```bash
#!/bin/bash
# /opt/internship-ai/scripts/backup.sh
BACKUP_DIR="/opt/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 备份数据库
docker exec internship_mysql_prod mysqldump -u internship -p$MYSQL_PASSWORD internship_db > $BACKUP_DIR/db_$TIMESTAMP.sql

# 备份Redis
docker exec internship_redis_prod redis-cli -a $REDIS_PASSWORD SAVE
cp /opt/internship-ai/data/redis/dump.rdb $BACKUP_DIR/redis_$TIMESTAMP.rdb

# 备份配置文件
tar czf $BACKUP_DIR/config_$TIMESTAMP.tar.gz /opt/internship-ai/nginx /opt/internship-ai/.env.prod

# 保留最近7天的备份
find $BACKUP_DIR -type f -mtime +7 -delete
```

### 定时任务
```bash
# /etc/crontab
0 2 * * * root /opt/internship-ai/scripts/backup.sh
```

## 验证步骤

### 服务器健康检查
```bash
# 1. 检查系统资源
free -h
df -h
top -bn1 | head -20

# 2. 检查服务状态
systemctl status docker
systemctl status nginx
systemctl status fail2ban

# 3. 检查网络连通性
ping -c 3 8.8.8.8
curl -I https://internship.example.com

# 4. 检查端口开放
netstat -tlnp
ss -tlnp
```

### 部署验证
```bash
# 1. 克隆代码
cd /opt
git clone https://github.com/your-org/internship-ai.git
cd internship-ai

# 2. 配置环境变量
cp .env.prod.template .env.prod
vim .env.prod  # 编辑配置

# 3. 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 4. 验证服务
docker-compose -f docker-compose.prod.yml ps
curl http://localhost:8000/health
```

## 故障排除

### 常见问题
1. **Docker容器启动失败**
   - 检查日志：`docker logs internship_backend_prod`
   - 检查端口冲突：`netstat -tlnp | grep :8000`

2. **数据库连接失败**
   - 验证MySQL服务运行：`docker exec internship_mysql_prod mysqladmin ping`
   - 检查连接字符串：`echo $DATABASE_URL`

3. **内存不足**
   - 检查内存使用：`free -h`
   - 调整Docker内存限制：`docker update --memory 2g internship_backend_prod`

## 附录

### 服务器采购申请表
| 项目 | 内容 |
|------|------|
| 项目名称 | 学生求职AI助手 |
| 申请部门 | 技术部 |
| 申请人 | 张三 |
| 申请时间 | 2026-04-11 |
| 服务器用途 | 生产环境应用部署 |
| 预计用户量 | 初期1000DAU |
| 带宽需求 | 5Mbps（可弹性扩展） |
| 数据盘需求 | 100G SSD（应用）+200G SSD（数据库） |
| 备份策略 | 每日自动备份，保留7天 |
| 安全要求 | 安全组策略、DDoS防护、WAF |

### 联系人信息
- **运维负责人**：李四，13800138000，lisi@example.com
- **技术支持**：王五，13900139000，wangwu@example.com
- **紧急联系电话**：400-123-4567