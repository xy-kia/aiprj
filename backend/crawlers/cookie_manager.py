"""
Cookie管理器 - 管理和自动更新Cookie
"""

import json
import time
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class CookieManager:
    """
    Cookie管理器

    功能：
    1. 管理多个站点的Cookie
    2. 自动检测Cookie过期
    3. 持久化存储Cookie
    4. 自动更新Cookie
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        default_ttl: int = 3600  # 默认Cookie有效期1小时
    ):
        """
        初始化Cookie管理器

        Args:
            storage_path: Cookie存储文件路径
            default_ttl: 默认Cookie有效期(秒)
        """
        self.storage_path = Path(storage_path) if storage_path else None
        self.default_ttl = default_ttl
        self._cookies: Dict[str, Dict[str, Any]] = {}
        self._last_updated: Dict[str, datetime] = {}

        if self.storage_path and self.storage_path.exists():
            self.load()

    def get(self, site: str) -> Optional[Dict[str, str]]:
        """
        获取指定站点的Cookie

        Args:
            site: 站点标识

        Returns:
            Cookie字典或None
        """
        if site not in self._cookies:
            return None

        # 检查是否过期
        if self.is_expired(site):
            logger.warning(f"Cookie for {site} has expired")
            return None

        return self._cookies[site].get("data")

    def set(
        self,
        site: str,
        cookies: Dict[str, str],
        ttl: Optional[int] = None
    ):
        """
        设置站点Cookie

        Args:
            site: 站点标识
            cookies: Cookie数据
            ttl: 有效期(秒)
        """
        self._cookies[site] = {
            "data": cookies,
            "expires_at": time.time() + (ttl or self.default_ttl),
            "created_at": time.time()
        }
        self._last_updated[site] = datetime.now()

        logger.info(f"Cookie set for {site}")

        # 自动保存
        if self.storage_path:
            self.save()

    def update(self, site: str, cookies: Dict[str, str]):
        """
        更新站点Cookie（合并）

        Args:
            site: 站点标识
            cookies: 新的Cookie数据
        """
        existing = self.get(site) or {}
        existing.update(cookies)
        self.set(site, existing)

    def update_cookies(self, cookies):
        """
        从响应对象更新Cookie

        Args:
            cookies: httpx.Cookies或类似对象
        """
        # 此方法供爬虫调用，自动处理
        pass

    def is_expired(self, site: str) -> bool:
        """
        检查Cookie是否过期

        Args:
            site: 站点标识

        Returns:
            是否过期
        """
        if site not in self._cookies:
            return True

        expires_at = self._cookies[site].get("expires_at", 0)
        return time.time() > expires_at

    def clear(self, site: Optional[str] = None):
        """
        清除Cookie

        Args:
            site: 站点标识，None则清除所有
        """
        if site:
            self._cookies.pop(site, None)
            self._last_updated.pop(site, None)
            logger.info(f"Cleared cookies for {site}")
        else:
            self._cookies.clear()
            self._last_updated.clear()
            logger.info("Cleared all cookies")

        if self.storage_path:
            self.save()

    def save(self):
        """保存Cookie到文件"""
        if not self.storage_path:
            return

        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "cookies": self._cookies,
                    "last_updated": {
                        k: v.isoformat()
                        for k, v in self._last_updated.items()
                    }
                }, f, ensure_ascii=False, indent=2)
            logger.debug(f"Cookies saved to {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")

    def load(self):
        """从文件加载Cookie"""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._cookies = data.get("cookies", {})

            # 解析时间戳
            for site, ts in data.get("last_updated", {}).items():
                try:
                    self._last_updated[site] = datetime.fromisoformat(ts)
                except:
                    self._last_updated[site] = datetime.now()

            logger.info(f"Loaded cookies for {len(self._cookies)} sites")

            # 清理过期Cookie
            self._clean_expired()

        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")

    def _clean_expired(self):
        """清理过期Cookie"""
        expired = [
            site for site in self._cookies.keys()
            if self.is_expired(site)
        ]
        for site in expired:
            del self._cookies[site]
            del self._last_updated[site]
            logger.info(f"Removed expired cookies for {site}")

    def get_all_sites(self) -> list:
        """获取所有站点列表"""
        return list(self._cookies.keys())

    def get_stats(self) -> Dict[str, Any]:
        """获取Cookie统计信息"""
        stats = {
            "total_sites": len(self._cookies),
            "expired": 0,
            "active": 0,
            "sites": {}
        }

        for site in self._cookies:
            is_exp = self.is_expired(site)
            if is_exp:
                stats["expired"] += 1
            else:
                stats["active"] += 1

            stats["sites"][site] = {
                "expired": is_exp,
                "last_updated": self._last_updated.get(site)
            }

        return stats


class RotatingCookieManager(CookieManager):
    """
    轮换Cookie管理器

    支持多账号Cookie轮换使用
    """

    def __init__(self, storage_path: Optional[str] = None, default_ttl: int = 3600):
        super().__init__(storage_path, default_ttl)
        self._cookie_pools: Dict[str, list] = {}
        self._current_index: Dict[str, int] = {}

    def add_to_pool(self, site: str, cookies: Dict[str, str]):
        """
        添加Cookie到轮换池

        Args:
            site: 站点标识
            cookies: Cookie数据
        """
        if site not in self._cookie_pools:
            self._cookie_pools[site] = []
            self._current_index[site] = 0

        self._cookie_pools[site].append({
            "data": cookies,
            "expires_at": time.time() + self.default_ttl,
            "fail_count": 0
        })

    def get_next(self, site: str) -> Optional[Dict[str, str]]:
        """
        获取下一个Cookie（轮换）

        Args:
            site: 站点标识

        Returns:
            Cookie字典或None
        """
        if site not in self._cookie_pools:
            return self.get(site)

        pool = self._cookie_pools[site]
        if not pool:
            return None

        # 获取当前索引的Cookie
        idx = self._current_index.get(site, 0)
        cookie_data = pool[idx]

        # 移动到下一个
        self._current_index[site] = (idx + 1) % len(pool)

        # 检查是否过期
        if time.time() > cookie_data.get("expires_at", 0):
            return self.get_next(site)  # 递归获取下一个

        return cookie_data.get("data")

    def mark_failed(self, site: str, cookies: Dict[str, str]):
        """
        标记Cookie失败

        Args:
            site: 站点标识
            cookies: 失败的Cookie
        """
        if site not in self._cookie_pools:
            return

        for item in self._cookie_pools[site]:
            if item.get("data") == cookies:
                item["fail_count"] = item.get("fail_count", 0) + 1

                # 失败次数过多，从池中移除
                if item["fail_count"] > 3:
                    self._cookie_pools[site].remove(item)
                    logger.warning(f"Removed failed cookie from {site} pool")
                break


# 便捷函数
def create_cookie_manager(
    storage_path: str = "./data/cookies.json",
    rotating: bool = False
) -> CookieManager:
    """
    创建Cookie管理器

    Args:
        storage_path: 存储路径
        rotating: 是否使用轮换模式

    Returns:
        CookieManager实例
    """
    if rotating:
        return RotatingCookieManager(storage_path)
    return CookieManager(storage_path)
