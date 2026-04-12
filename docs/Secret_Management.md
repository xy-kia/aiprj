# 密钥管理方案

## 概述
本文档描述了学生求职AI助手项目的密钥管理方案，确保敏感信息（API密钥、数据库密码等）的安全存储和使用。

## 密钥分类

### 1. 基础设施密钥
| 密钥类型 | 存储位置 | 访问控制 | 轮换策略 |
|----------|----------|----------|----------|
| 数据库密码 | AWS Secrets Manager / HashiCorp Vault | 仅限运维团队 | 每90天 |
| Redis密码 | AWS Secrets Manager / HashiCorp Vault | 仅限运维团队 | 每90天 |
| 服务器SSH密钥 | 密钥管理服务 | 仅限授权运维人员 | 每180天 |

### 2. 第三方服务密钥
| 服务 | 密钥类型 | 存储位置 | 访问控制 |
|------|----------|----------|----------|
| OpenAI | API密钥 | AWS Secrets Manager | 后端服务账号 |
| Anthropic | API密钥 | AWS Secrets Manager | 后端服务账号 |
| 邮件服务 | SMTP凭证 | AWS Secrets Manager | 后端服务账号 |
| 监控服务 | 访问令牌 | AWS Secrets Manager | 监控服务账号 |

### 3. 应用密钥
| 密钥类型 | 用途 | 存储位置 | 生成方式 |
|----------|------|----------|----------|
| JWT签名密钥 | 令牌签名 | 环境变量 | 随机生成，长度≥32字符 |
| 会话密钥 | 会话加密 | 环境变量 | 随机生成，长度≥64字符 |
| 加密盐值 | 密码哈希 | 环境变量 | 随机生成，长度≥16字符 |

## 存储方案

### 生产环境
1. **主要存储**：使用AWS Secrets Manager或HashiCorp Vault
2. **备份存储**：加密存储在S3桶中
3. **本地缓存**：应用程序启动时从密钥管理服务加载

### 开发/测试环境
1. **本地开发**：使用`.env.local`文件（加入`.gitignore`）
2. **CI/CD管道**：使用GitHub Secrets或GitLab CI Variables
3. **测试环境**：使用独立的密钥管理服务实例

## 密钥注入方式

### Docker容器
```yaml
# docker-compose.prod.yml示例
services:
  backend:
    environment:
      - DATABASE_PASSWORD=${DATABASE_PASSWORD}
    secrets:
      - openai_api_key
      - anthropic_api_key

secrets:
  openai_api_key:
    external: true
  anthropic_api_key:
    external: true
```

### Kubernetes
```yaml
# Kubernetes Secret示例
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
data:
  openai-api-key: <base64-encoded>
  database-password: <base64-encoded>
```

### 应用程序加载
```python
# 密钥加载示例
import os
from aws_secretsmanager_caching import SecretCache, SecretCacheConfig

# 从环境变量或密钥管理服务加载
def load_secret(secret_name: str, default: str = None) -> str:
    # 1. 检查环境变量
    env_var = f"{secret_name.upper().replace('-', '_')}"
    if value := os.getenv(env_var):
        return value
    
    # 2. 从AWS Secrets Manager加载
    try:
        cache = SecretCache()
        return cache.get_secret_string(secret_name)
    except Exception:
        pass
    
    # 3. 返回默认值或抛出异常
    if default is not None:
        return default
    raise ValueError(f"Secret {secret_name} not found")
```

## 访问控制

### 权限模型
1. **最小权限原则**：每个服务/用户仅获取所需密钥
2. **角色分离**：开发、运维、监控角色权限分离
3. **审计日志**：所有密钥访问记录日志

### 访问审批流程
```
密钥访问请求 → 安全团队审批 → 临时授权 → 自动过期 → 审计报告
```

## 密钥轮换

### 自动轮换策略
1. **数据库密码**：每90天自动轮换，应用程序无感知
2. **API密钥**：每180天轮换，保留旧密钥7天用于回滚
3. **SSL证书**：每90天自动更新

### 轮换步骤
```bash
# 1. 生成新密钥
$ generate-new-secret --type database-password

# 2. 更新密钥管理服务
$ aws secretsmanager update-secret --secret-id database-password --secret-string "new-password"

# 3. 通知应用程序重新加载（通过SNS或配置更新）
$ trigger-config-reload --service backend

# 4. 验证新密钥工作正常
$ verify-connection --database --password new-password

# 5. 删除旧密钥（保留7天后）
$ schedule-secret-deletion --secret-id database-password --days 7
```

## 监控与告警

### 监控指标
| 指标 | 阈值 | 告警级别 |
|------|------|----------|
| 密钥访问失败率 | >5% | P1 |
| 密钥即将过期 | <7天 | P2 |
| 异常访问模式 | 检测到异常 | P0 |

### 审计要求
1. 所有密钥访问记录保存180天
2. 定期审计密钥使用情况（每月）
3. 异常访问立即通知安全团队

## 应急响应

### 密钥泄露处理流程
1. **立即响应**：
   - 将泄露密钥标记为"已泄露"
   - 阻断使用该密钥的访问
   - 启动安全事件响应流程

2. **密钥替换**：
   - 生成新密钥
   - 更新所有使用该密钥的服务
   - 验证服务正常运行

3. **事后分析**：
   - 调查泄露原因
   - 修复安全漏洞
   - 更新安全策略

### 回滚流程
1. 恢复上一版本密钥
2. 验证服务可用性
3. 分析轮换失败原因

## 合规要求

### 数据保护法规
- **GDPR**：密钥作为个人数据处理，需加密存储
- **等保2.0**：三级系统要求密钥管理系统认证
- **ISO 27001**：要求密钥生命周期管理

### 审计证明
1. 密钥生成记录
2. 访问审计日志
3. 轮换操作记录
4. 泄露响应报告

## 附录

### 密钥命名规范
```
{环境}-{服务}-{类型}-{序号}
示例：
- prod-database-password-01
- staging-openai-api-key-01
- dev-redis-password-01
```

### 密钥生成工具
```bash
# 生成随机密码
$ openssl rand -base64 32

# 生成JWT密钥
$ openssl rand -hex 32

# 生成加密盐值
$ openssl rand -base64 16
```

### 参考文档
- [AWS Secrets Manager最佳实践](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [HashiCorp Vault部署指南](https://www.vaultproject.io/docs)
- [NIST密钥管理指南](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final)