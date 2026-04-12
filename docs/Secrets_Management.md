# 密钥管理与安全配置指南

## 概述

本文档描述生产环境中敏感配置信息（API密钥、数据库密码等）的管理方案，确保密钥安全存储，避免硬编码在代码中。

## 密钥存储方案

### 1. 环境变量（推荐）
- 使用 `.env.prod` 文件存储开发/测试环境密钥
- 生产环境使用容器环境变量或托管平台密钥管理服务
- **重要**：`.env.prod` 文件必须添加到 `.gitignore`，禁止提交到版本控制

### 2. 密钥管理服务
根据部署平台选择密钥管理服务：

| 平台 | 服务 | 说明 |
|------|------|------|
| Docker | Docker Secrets | 适用于 Swarm 模式 |
| Kubernetes | Kubernetes Secrets | 原生 Secret 对象 |
| AWS | AWS Secrets Manager | 企业级密钥管理 |
| Azure | Azure Key Vault | Azure 平台集成 |
| GCP | Google Secret Manager | GCP 平台集成 |
| 自建 | HashiCorp Vault | 开源密钥管理 |

### 3. 多环境密钥分离

| 环境 | 密钥来源 | 示例 |
|------|----------|------|
| 开发 | `.env.dev` 本地文件 | 开发人员本地测试 |
| 测试 | `.env.staging` 文件 | CI/CD 流水线注入 |
| 生产 | 平台密钥管理服务 | AWS Secrets Manager |

## 密钥轮换策略

### 1. 自动轮换
- **数据库密码**：每90天自动轮换
- **API密钥**：根据供应商建议轮换（通常180天）
- **SSL证书**：Let's Encrypt 证书90天自动续期

### 2. 轮换步骤
1. 生成新密钥并更新到密钥管理服务
2. 分阶段更新应用配置（灰度发布）
3. 验证新密钥正常工作
4. 废弃旧密钥（保留7天应急回滚）

## 具体密钥清单

### 必须管理的密钥

| 密钥名称 | 类型 | 敏感级别 | 轮换周期 | 存储位置示例 |
|----------|------|----------|----------|--------------|
| `MYSQL_ROOT_PASSWORD` | 数据库密码 | P0（最高） | 90天 | AWS Secrets Manager |
| `MYSQL_PASSWORD` | 应用数据库密码 | P0 | 90天 | Kubernetes Secrets |
| `REDIS_PASSWORD` | 缓存密码 | P0 | 180天 | 环境变量注入 |
| `OPENAI_API_KEY` | API密钥 | P1 | 180天 | HashiCorp Vault |
| `ANTHROPIC_API_KEY` | API密钥 | P1 | 180天 | HashiCorp Vault |
| `SECRET_KEY` | 应用签名密钥 | P0 | 90天 | 平台密钥管理 |
| `JWT_SECRET_KEY` | JWT签名密钥 | P0 | 90天 | 平台密钥管理 |

### 可选密钥
| 密钥名称 | 类型 | 敏感级别 | 说明 |
|----------|------|----------|------|
| `SENTRY_DSN` | 监控服务密钥 | P2 | 错误跟踪 |
| `EMAIL_PASSWORD` | 邮件服务密码 | P1 | 通知服务 |
| `SMS_API_KEY` | 短信服务密钥 | P1 | 通知服务 |

## 安全实践

### 1. 开发环境
```bash
# 使用示例密钥，避免真实密钥泄露
cp .env.example .env.prod
# 编辑 .env.prod 文件，填入测试密钥
```

### 2. CI/CD 流水线
```yaml
# GitHub Actions 示例
env:
  MYSQL_PASSWORD: ${{ secrets.MYSQL_PASSWORD }}
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### 3. 生产部署
```bash
# Docker Compose 使用环境变量文件
docker-compose --env-file .env.prod up -d

# Kubernetes 使用 Secret
kubectl create secret generic app-secrets --from-env-file=.env.prod
```

### 4. 密钥注入验证
部署后验证密钥是否正确注入：
```bash
# 检查环境变量
docker exec <container> env | grep -E "(PASSWORD|KEY|SECRET)"

# 验证 API 连通性
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

## 应急响应

### 密钥泄露处理流程
1. **立即轮换**：在密钥管理服务中立即禁用泄露密钥
2. **审计日志**：检查密钥使用记录，确定泄露范围
3. **通知相关方**：通知可能受影响的服务和用户
4. **根本原因分析**：调查泄露原因，修复安全漏洞

### 回滚方案
保留旧密钥7天，确保紧急回滚能力：
```bash
# 快速回滚到上一版本密钥
kubectl rollout undo deployment/app-deployment
```

## 合规要求

### 1. 访问控制
- 最小权限原则：仅授予必要人员密钥访问权限
- 操作审计：所有密钥访问操作记录日志
- 定期审查：每季度审查密钥访问权限

### 2. 加密存储
- 静态加密：密钥在存储时必须加密
- 传输加密：密钥传输使用 TLS 1.2+
- 内存保护：避免密钥在日志或内存中明文暴露

### 3. 监控告警
- 异常访问检测：非常规时间/IP的密钥访问
- 失败尝试监控：多次密钥验证失败
- 使用量监控：API密钥异常使用模式

## 附录

### 密钥生成最佳实践
```bash
# 生成强密码
openssl rand -base64 32

# 生成 JWT 密钥
openssl rand -base64 64

# 生成数据库密码
pwgen -s 32 1
```

### 常用工具
- `openssl`：密钥生成和加密
- `pwgen`：密码生成
- `sops`：加密文件编辑
- `git-secret`：Git仓库密钥管理

---

**文档版本**: 1.0  
**更新日期**: 2026-04-11  
**负责人**: 运维团队