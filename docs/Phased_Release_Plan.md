# 渐进式发布计划（小流量→中流量→全量）

## 概述

本文档描述 Internship AI Assistant 生产环境的渐进式发布策略，通过小流量、中流量、全量三个阶段逐步发布新版本，最大化降低发布风险。

## 发布原则

### 1. 核心原则
- **风险可控**: 分阶段逐步扩大流量，及时发现并修复问题
- **快速回滚**: 每个阶段都准备完整的回滚方案
- **监控驱动**: 基于监控数据决定是否推进到下一阶段
- **用户影响最小化**: 优先影响内部用户，逐步扩大到外部用户

### 2. 发布阶段

| 阶段 | 流量比例 | 目标用户 | 持续时间 | 主要目标 |
|------|----------|----------|----------|----------|
| 内部测试 | 0% | 测试团队 | 1-2天 | 功能完整性验证 |
| 小流量发布 | 5% | 内部员工+少量真实用户 | 6-12小时 | 稳定性验证 |
| 中流量发布 | 20% | 早期采用者+部分用户 | 12-24小时 | 性能压力测试 |
| 全量发布 | 100% | 所有用户 | 永久 | 功能全面上线 |

### 3. 成功标准

| 阶段 | 技术指标 | 业务指标 | 用户反馈 |
|------|----------|----------|----------|
| 小流量 | 错误率 < 1% | 核心功能正常 | 无用户投诉 |
| 中流量 | 错误率 < 0.5% | 转化率稳定 | 满意度 ≥ 4/5 |
| 全量 | 错误率 < 0.1% | 核心指标正常 | 无重大问题 |

## 发布前准备

### 1. 预发布检查清单

#### 代码质量
- [ ] 所有自动化测试通过
- [ ] 代码审查完成
- [ ] 安全扫描通过
- [ ] 性能基准测试通过
- [ ] 依赖包版本已锁定

#### 部署准备
- [ ] Docker 镜像已构建并推送到仓库
- [ ] 数据库迁移脚本已准备好
- [ ] 配置文件已更新（生产环境）
- [ ] SSL 证书有效
- [ ] 监控告警已配置

#### 团队准备
- [ ] 发布计划已沟通
- [ ] 相关人员已通知
- [ ] 值班安排已确认
- [ ] 应急联系渠道已建立

### 2. 回滚准备
```bash
# 创建完整备份
./scripts/backup.sh production full

# 备份包含：
# 1. 数据库全量备份
# 2. Redis 数据备份
# 3. 配置文件备份
# 4. 当前运行容器状态
```

### 3. 监控仪表板
确保以下监控仪表板就绪：
- 实时错误率监控
- 响应时间监控（P50, P95, P99）
- 业务指标监控（搜索成功率、用户满意度）
- 资源使用监控（CPU、内存、磁盘）

## 阶段1：小流量发布（5%用户）

### 1. 发布目标
- 验证新版本在生产环境的基本稳定性
- 收集初步的性能数据
- 确保核心功能正常工作

### 2. 流量分配策略

#### 用户选择标准
- 50% 内部员工（技术、产品、测试团队）
- 30% 友好用户（自愿参与测试的用户）
- 20% 随机真实用户

#### 流量路由配置
```nginx
# nginx 配置 - 基于 Cookie 的流量切分
map $cookie_canary $backend_pool {
    default "backend-prod";      # 95% 流量到老版本
    "canary" "backend-canary";   # 5% 流量到新版本
}

server {
    location / {
        proxy_pass http://$backend_pool;
        
        # 设置 Canary Cookie（仅对特定用户）
        add_header Set-Cookie "canary=1; Path=/; Max-Age=3600" if=$canary_user;
    }
}

# 基于用户 ID 哈希的流量切分
map $cookie_user_id $backend_by_user {
    default "backend-prod";
    ~* "^(1|5|9|13|17)" "backend-canary";  # 用户 ID 以特定数字结尾
}
```

#### 替代方案：基于权重的负载均衡
```yaml
# docker-compose 配置
services:
  nginx:
    image: nginx
    volumes:
      - ./nginx/canary.conf:/etc/nginx/nginx.conf

# nginx canary.conf
upstream backend {
    server backend-prod:8000 weight=95;  # 95% 流量
    server backend-canary:8000 weight=5; # 5% 流量
}
```

### 3. 发布步骤

#### 步骤1：部署 Canary 版本
```bash
# 部署 Canary 版本（与生产版本并行运行）
./scripts/deploy_canary.sh

# 验证 Canary 版本健康状态
curl -f http://backend-canary:8000/health
```

#### 步骤2：配置流量路由
```bash
# 更新 Nginx 配置，引入 5% 流量
./scripts/update_nginx_canary.sh 5

# 重新加载 Nginx
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

#### 步骤3：监控与观察
```bash
# 监控关键指标
watch -n 5 '
echo "=== Canary 监控 ==="
echo "错误率: $(curl -s http://prometheus:9090/api/v1/query?query=rate(http_requests_total{status=~"5..",instance="backend-canary:8000"}[5m]))"
echo "响应时间 P95: $(curl -s http://prometheus:9090/api/v1/query?query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{instance="backend-canary:8000"}[5m])))"
echo "流量比例: $(curl -s http://prometheus:9090/api/v1/query?query=sum(rate(http_requests_total{instance="backend-canary:8000"}[5m])) / sum(rate(http_requests_total[5m])))"
'
```

### 4. 验证标准

#### 技术指标（持续6小时）
| 指标 | 阈值 | 检查频率 | 说明 |
|------|------|----------|------|
| 错误率 | < 1% | 每分钟 | HTTP 5xx 错误比例 |
| 响应时间 P95 | < 2s | 每分钟 | 95% 请求响应时间 |
| 服务可用性 | > 99.5% | 每分钟 | 健康检查通过率 |
| 内存泄漏 | < 10MB/h | 每小时 | 内存增长速率 |

#### 业务指标
| 指标 | 基线 | 当前值 | 变化允许范围 |
|------|------|--------|--------------|
| 搜索成功率 | 85% | ≥ 84% | -1% |
| 用户满意度 | 4.2/5 | ≥ 4.0 | -0.2 |
| 转化率 | 12% | ≥ 11.5% | -0.5% |

### 5. 决策点

#### 继续推进条件（满足所有）
1. 错误率 < 1% 持续 4 小时
2. 无重大功能缺陷报告
3. 用户反馈无严重问题
4. 核心业务指标正常

#### 回滚条件（满足任一）
1. 错误率 > 5% 持续 15 分钟
2. 发现数据丢失或损坏
3. 安全漏洞暴露
4. 核心功能完全不可用

### 6. 回滚操作
```bash
# 立即回滚到 100% 老版本流量
./scripts/rollback_canary.sh

# 验证回滚效果
curl -f http://backend-prod:8000/health
```

## 阶段2：中流量发布（20%用户）

### 1. 发布目标
- 验证新版本在较高负载下的稳定性
- 测试数据库迁移、缓存等基础设施
- 收集更多用户反馈

### 2. 流量分配策略

#### 用户扩展策略
- 保留原有的 5% Canary 用户
- 新增 15% 随机真实用户
- 重点关注关键用户群体（高频用户、付费用户）

#### 地理分布考虑
```nginx
# 基于地理位置的流量分配
geo $canary_region {
    default 0;
    # 北京、上海、广州用户优先体验新版本
    116.0.0.0/8 1;  # 北京
    58.0.0.0/8 1;   # 上海
    113.0.0.0/8 1;  # 广州
}

map $canary_region $backend_pool {
    0 "backend-prod";     # 80% 流量
    1 "backend-canary";   # 20% 流量
}
```

### 3. 发布步骤

#### 步骤1：扩大流量比例
```bash
# 将流量从 5% 提升到 20%
./scripts/update_nginx_canary.sh 20

# 逐步增加，每小时增加 5%
for percent in 10 15 20; do
    ./scripts/update_nginx_canary.sh $percent
    sleep 3600  # 观察 1 小时
done
```

#### 步骤2：执行数据迁移
```bash
# 运行数据库迁移（向后兼容）
./scripts/run_migrations.sh canary

# 验证迁移结果
./scripts/verify_migrations.sh
```

#### 步骤3：压力测试
```bash
# 模拟中流量负载
./scripts/load_test.sh --users 1000 --duration 30m

# 监控性能表现
./scripts/monitor_performance.sh --stage medium
```

### 4. 验证标准

#### 技术指标（持续12小时）
| 指标 | 阈值 | 检查频率 |
|------|------|----------|
| 错误率 | < 0.5% | 每分钟 |
| 响应时间 P95 | < 1.5s | 每分钟 |
| 数据库连接池使用率 | < 80% | 每分钟 |
| 缓存命中率 | > 85% | 每分钟 |

#### 业务指标
| 指标 | 基线 | 当前值 | 变化允许范围 |
|------|------|--------|--------------|
| 用户活跃度 | 基准值 | ±10% | 允许波动 |
| 功能使用率 | 基准值 | ±5% | 允许波动 |
| 用户留存率 | 基准值 | ±2% | 允许波动 |

### 5. 用户反馈收集

#### 反馈渠道
1. **应用内反馈表单**: 收集 Canary 用户的直接反馈
2. **用户行为分析**: 对比新老版本用户行为差异
3. **客服渠道**: 监控用户投诉和咨询
4. **社交媒体**: 关注用户公开讨论

#### 反馈分类
```yaml
feedback_categories:
  critical:
    - 功能完全不可用
    - 数据丢失或错误
    - 安全问题
  major:
    - 主要功能性能下降
    - 用户体验显著变差
    - 关键流程中断
  minor:
    - 界面显示问题
    - 非核心功能问题
    - 建议和改进
```

### 6. 决策点

#### 继续推进条件
1. 错误率 < 0.5% 持续 8 小时
2. 用户满意度 ≥ 4/5
3. 无 critical 级别反馈
4. 业务指标在正常波动范围内

#### 回滚条件
1. 错误率 > 2% 持续 30 分钟
2. 收到 critical 级别反馈
3. 核心业务指标下降 > 5%
4. 数据库性能严重下降

## 阶段3：全量发布（100%用户）

### 1. 发布目标
- 将所有用户流量切换到新版本
- 完成最终的数据迁移和清理
- 确保平稳过渡

### 2. 发布策略

#### 最终切换
```bash
# 一次性切换 100% 流量
./scripts/update_nginx_canary.sh 100

# 或者分批次切换（更安全）
for percent in 40 60 80 100; do
    ./scripts/update_nginx_canary.sh $percent
    sleep 1800  # 观察 30 分钟
done
```

#### 旧版本清理
```bash
# 停止并移除旧版本容器
docker-compose -f docker-compose.prod.yml stop backend-prod
docker-compose -f docker-compose.prod.yml rm -f backend-prod

# 清理旧版本镜像
docker image prune -a --filter "label=version=old"
```

### 3. 发布步骤

#### 步骤1：最终验证
```bash
# 运行完整的功能测试
./scripts/run_full_test_suite.sh

# 性能基准测试
./scripts/run_benchmark.sh --baseline v1.1.0 --current v1.2.0
```

#### 步骤2：流量切换
```bash
# 宣布维护窗口（如果需要）
./scripts/announce_maintenance.sh --start "2026-04-11 02:00" --duration "1h"

# 执行最终切换
./scripts/final_cutover.sh

# 验证切换结果
./scripts/verify_cutover.sh
```

#### 步骤3：后续清理
```bash
# 执行最终数据迁移（如有破坏性变更）
./scripts/run_final_migrations.sh

# 清理临时文件
./scripts/cleanup_temp_files.sh

# 更新监控标签
./scripts/update_monitoring_labels.sh --version v1.2.0
```

### 4. 验证标准

#### 技术指标（持续24小时）
| 指标 | 阈值 | 检查频率 |
|------|------|----------|
| 整体错误率 | < 0.1% | 每分钟 |
| 整体响应时间 P95 | < 1s | 每分钟 |
| 系统可用性 | > 99.9% | 每分钟 |
| 资源使用率 | < 70% | 每分钟 |

#### 业务指标（持续48小时）
| 指标 | 期望值 | 监控频率 |
|------|--------|----------|
| 核心业务成功率 | ≥ 95% | 每小时 |
| 用户满意度 | ≥ 4.5/5 | 每天 |
| 系统吞吐量 | ≥ 基线值 | 每小时 |

### 5. 发布后监控

#### 增强监控（发布后72小时）
```bash
# 设置增强监控
./scripts/enable_enhanced_monitoring.sh --duration 72h

# 监控项包括：
# 1. 细粒度错误分类
# 2. 用户行为异常检测
# 3. 性能回归检测
# 4. 资源泄漏检测
```

#### 用户反馈处理
```bash
# 设立发布后专项支持
./scripts/setup_post_release_support.sh

# 反馈处理流程：
# 1. 实时监控用户反馈
# 2. 快速分类和响应
# 3. 紧急问题升级流程
# 4. 定期反馈汇总
```

### 6. 应急预案

#### 快速回滚方案
```bash
# 全量回滚到上一个稳定版本
./scripts/full_rollback.sh --version v1.1.0

# 回滚包含：
# 1. 100% 流量切回旧版本
# 2. 数据库回滚（如果需要）
# 3. 配置回滚
# 4. 通知用户
```

#### 部分回滚方案
```bash
# 仅回滚有问题的功能模块
./scripts/partial_rollback.sh --module search_service

# 降级到兼容模式
./scripts/degrade_to_compatibility_mode.sh
```

## 发布后活动

### 1. 发布总结

#### 成功指标评估
```markdown
# 发布总结报告

## 发布概况
- **版本**: v1.2.0
- **发布时间**: 2026-04-11
- **总耗时**: 36小时
- **发布结果**: ✅ 成功

## 关键指标
| 指标 | 目标值 | 实际值 | 状态 |
|------|--------|--------|------|
| 错误率 | < 0.1% | 0.05% | ✅ |
| 响应时间 P95 | < 1s | 0.8s | ✅ |
| 用户满意度 | ≥ 4.5 | 4.7 | ✅ |
| 业务成功率 | ≥ 95% | 97.2% | ✅ |

## 遇到的问题
1. 小流量阶段发现数据库连接泄漏（已修复）
2. 中流量阶段某个 API 响应变慢（已优化）

## 改进建议
1. 加强数据库连接池监控
2. 增加更细粒度的性能测试

## 团队表现
- 开发团队: ✅
- 测试团队: ✅
- 运维团队: ✅
- 产品团队: ✅
```

### 2. 知识沉淀

#### 经验总结
- 成功经验和最佳实践
- 遇到的问题和解决方案
- 工具和脚本的改进点

#### 文档更新
- 更新部署文档
- 更新故障处理手册
- 更新监控配置文档

### 3. 庆祝与认可
- 发布成功庆祝会
- 团队成员认可
- 经验分享会

## 附录

### 发布日历示例
```markdown
## 发布日历 v1.2.0

### 第1天：准备与内部测试
- 08:00-10:00 预发布检查
- 10:00-12:00 部署到测试环境
- 12:00-18:00 内部测试验证
- 18:00-20:00 发布准备会议

### 第2天：小流量发布
- 02:00-03:00 部署 Canary 版本
- 03:00-09:00 5% 流量，监控观察
- 09:00-12:00 问题修复（如有）
- 12:00-18:00 继续观察
- 18:00-20:00 阶段评审会

### 第3天：中流量发布
- 02:00-08:00 逐步提升到 20% 流量
- 08:00-20:00 监控和用户反馈收集
- 20:00-22:00 阶段评审会

### 第4天：全量发布
- 02:00-04:00 全量切换准备
- 04:00-06:00 分批次切换至 100%
- 06:00-18:00 发布后监控
- 18:00-20:00 发布总结会
```

### 紧急联系人列表
| 角色 | 姓名 | 电话 | 在线状态 |
|------|------|------|----------|
| 发布经理 | 张三 | 138-xxxx-xxxx | 24/7 |
| 技术负责人 | 李四 | 139-xxxx-xxxx | 24/7 |
| 运维值班 | 王五 | 137-xxxx-xxxx | 24/7 |
| 产品负责人 | 赵六 | 136-xxxx-xxxx | 08:00-22:00 |

### 工具和脚本
- `scripts/deploy_canary.sh` - Canary 部署脚本
- `scripts/update_nginx_canary.sh` - 流量控制脚本
- `scripts/monitor_release.sh` - 发布监控脚本
- `scripts/rollback_canary.sh` - Canary 回滚脚本
- `scripts/full_rollback.sh` - 全量回滚脚本

---

**文档版本**: 1.0  
**更新日期**: 2026-04-11  
**负责人**: 发布管理团队