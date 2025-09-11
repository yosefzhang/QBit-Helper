import os
import logging
import yaml
from dataclasses import dataclass, field
from typing import List, Any, Dict, Optional, Set
import qbittorrentapi
from serverchan_sdk import sc_send
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

# 数据类定义
@dataclass
class TorrentInfo:
    """种子信息数据类"""
    hash: str
    name: str
    save_path: str
    size: int
    tags: List[str] = field(default_factory=list)
    comment: str = ''
    trackers: List[Any] = field(default_factory=list)

@dataclass
class DashboardInfo:
    """仪表板信息数据类"""
    total_torrents: int
    total_trackers: int
    non_working_trackers: int
    category_counts: Dict[str, int]
    tag_counts: Dict[str, int]

class QBitHelperBasic:
    def __init__(self, config: str):
        # 初始化config_data
        self.config_data = config
        with open(config, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # 初始化logging
        self.log_file = os.path.join('data', self.config.get('default', {}).get('logging', {}).get('filename', 'QBittorrent-Helper.log'))
        self.log_level = self.config.get('default', {}).get('logging', {}).get('level')
        logging.basicConfig(filename=self.log_file, level=self.log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
        self.logger = logging.getLogger(self.log_file)
        self.logger.info(f'加载配置文件：{os.path.abspath(config)}')

        # 初始化qbit_client
        self.init_qbit_client()
        
        # 初始化torrent_dict
        self.init_torrent_dict()
        
        # 初始化cron调度器
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        # 注册退出时停止调度器
        atexit.register(lambda: self.scheduler.shutdown())
        
        # 加载自动任务
        self.load_auto_tasks()
    
    def get_user_config(self):
        """获取用户配置"""
        return self.config.get('user_config', {})
    
    def save_user_config(self, new_config):
        """保存用户配置"""
        if not self.config.get('user_config'):
            self.config['user_config'] = {}
        self.config['user_config'].update(new_config)
        
        with open(self.config_data, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self.config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        self.logger.info("用户配置已保存")

    def get_user_rules(self):
        """获取用户规则配置"""
        return self.config.get('user_rules', [])
    
    def save_user_rules(self, new_config):
        """保存用户规则配置"""
        # new_config 应该是一个规则列表
        rules_list = new_config if isinstance(new_config, list) else new_config.get('rules', [])
        
        # 使用 OrderedDict 确保字段顺序固定
        ordered_rules = []
        for rule in rules_list:
            if isinstance(rule, dict):
                ordered_rule = {}
                # 按照固定顺序添加字段
                field_order = ['rule_name', 'rule_type', 'priority', 'opt_type', 'trackers', 'tag', 'tags', 'tracker']
                for field in field_order:
                    if field in rule:
                        ordered_rule[field] = rule[field]
                # 添加其他可能存在的字段
                for key, value in rule.items():
                    if key not in ordered_rule:
                        ordered_rule[key] = value
                ordered_rules.append(ordered_rule)
            else:
                ordered_rules.append(rule)
        
        # 直接替换整个 user_rules 部分
        self.config['user_rules'] = ordered_rules
        
        with open(self.config_data, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self.config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        self.logger.info("用户规则已保存")

    # 新增用户任务相关方法
    def get_user_tasks(self):
        """获取用户任务配置"""
        # user_tasks在配置文件中是一个列表，直接返回
        return {'tasks': self.config.get('user_tasks', [])}
    
    def save_user_tasks(self, new_config):
        """保存用户任务配置"""
        # new_config 应该包含一个 'tasks' 键，其值为任务列表
        tasks_list = new_config.get('tasks', [])
        
        # 使用 OrderedDict 确保字段顺序固定
        ordered_tasks = []
        for task in tasks_list:
            if isinstance(task, dict):
                ordered_task = {}
                # 按照固定顺序添加字段
                field_order = ['task_name', 'task_type', 'cron', 'rules']
                for field in field_order:
                    if field in task:
                        ordered_task[field] = task[field]
                # 添加其他可能存在的字段
                for key, value in task.items():
                    if key not in ordered_task:
                        ordered_task[key] = value
                ordered_tasks.append(ordered_task)
            else:
                ordered_tasks.append(task)
        
        # 直接替换整个 user_tasks 部分
        self.config['user_tasks'] = ordered_tasks
        
        with open(self.config_data, 'w', encoding='utf-8') as f:
            yaml.safe_dump(self.config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        self.logger.info("用户任务已保存")
        
        # 重新加载自动任务
        self.reload_auto_tasks()
        
    def reload_auto_tasks(self):
        """重新加载自动任务到调度器"""
        try:
            # 清空所有现有的自动任务
            self.scheduler.remove_all_jobs()
            
            # 重新加载自动任务
            self.load_auto_tasks()
            
            self.logger.info("自动任务已重新加载")
        except Exception as e:
            self.logger.error(f"重新加载自动任务时发生错误: {str(e)}")
    
    def load_auto_tasks(self):
        """加载自动任务到调度器"""
        try:
            user_tasks = self.get_user_tasks()
            tasks = user_tasks.get('tasks', [])
            
            for index, task in enumerate(tasks):
                # 只处理自动任务
                if task.get('task_type') == 'auto' and task.get('cron'):
                    self.add_auto_task_to_scheduler(index, task)
            
            self.logger.info(f"已加载 {len([t for t in tasks if t.get('task_type') == 'auto' and t.get('cron')])} 个自动任务")
        except Exception as e:
            self.logger.error(f"加载自动任务时发生错误: {str(e)}")
    
    def add_auto_task_to_scheduler(self, index, task):
        """将自动任务添加到调度器"""
        try:
            cron_expression = task.get('cron')
            task_name = task.get('task_name', f'自动任务{index}')
            
            # 创建cron触发器
            trigger = CronTrigger.from_crontab(cron_expression)
            
            # 添加任务到调度器
            job = self.scheduler.add_job(
                self.execute_auto_task,
                trigger=trigger,
                id=f"auto_task_{index}",
                name=task_name,
                args=[index, task]
            )
            
            self.logger.info(f"已添加自动任务: {task_name} (ID: {job.id})")
        except Exception as e:
            self.logger.error(f"添加自动任务 {task.get('task_name', '未命名')} 到调度器时发生错误: {str(e)}")
    
    def remove_auto_task_from_scheduler(self, index):
        """从调度器中移除自动任务"""
        try:
            job_id = f"auto_task_{index}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                self.logger.info(f"已从调度器中移除自动任务 ID: {job_id}")
        except Exception as e:
            self.logger.error(f"从调度器中移除自动任务 {index} 时发生错误: {str(e)}")
    
    def execute_auto_task(self, index, task):
        """执行自动任务"""
        try:
            task_name = task.get('task_name', f'自动任务{index}')
            rules_string = task.get('rules', '')
            
            self.logger.info(f"开始执行自动任务: {task_name}")
            
            # 解析规则字符串
            if rules_string:
                rule_names = rules_string.split('|')
                # 获取所有用户规则
                all_rules = self.get_user_rules()
                # 筛选出匹配的规则
                matched_rules = [rule for rule in all_rules if rule.get('rule_name') in rule_names]
            else:
                matched_rules = []
            
            # 执行任务
            result = self.opt_all_torrent(matched_rules)
            
            # 记录结果
            if result['failed_count'] == 0:
                self.logger.info(f"自动任务 \"{task_name}\" 执行成功，处理了{result['processed_count']}个种子")
                
                # 发送通知（如果配置了webhook）
                if self.config.get('user_config', {}).get('webhook', {}).get('serverchan', {}).get('sc_key'):
                    title = f"qBittorrent助手 - 自动任务执行成功"
                    desp = f"任务名称: {task_name}\n成功处理种子数: {result['processed_count']}\n跳过种子数: {result['skipped_count']}\n失败种子数: {result['failed_count']}"
                    self.send_webhook_to_serverchan(title, desp)
            else:
                self.logger.error(f"自动任务 \"{task_name}\" 执行完成，但有{result['failed_count']}个种子处理失败")
                
                # 发送通知（如果配置了webhook）
                if self.config.get('user_config', {}).get('webhook', {}).get('serverchan', {}).get('sc_key'):
                    title = f"qBittorrent助手 - 自动任务执行完成但有失败"
                    desp = f"任务名称: {task_name}\n成功处理种子数: {result['processed_count']}\n跳过种子数: {result['skipped_count']}\n失败种子数: {result['failed_count']}\n失败详情: {', '.join(result['failed_details'])}"
                    self.send_webhook_to_serverchan(title, desp)
        except Exception as e:
            self.logger.error(f"执行自动任务 \"{task.get('task_name', '未命名')}\" 时发生错误: {str(e)}")
            
            # 发送通知（如果配置了webhook）
            if self.config.get('user_config', {}).get('webhook', {}).get('serverchan', {}).get('sc_key'):
                title = f"qBittorrent助手 - 自动任务执行异常"
                desp = f"任务名称: {task.get('task_name', '未命名')}\n错误信息: {str(e)}"
                self.send_webhook_to_serverchan(title, desp)

    def send_webhook_to_serverchan(self, title: str, desp: str, tags: Optional[str] = None) -> bool:
        """发送消息到Server酱"""
        try:
            # 从新配置结构中获取 sc_key
            sc_key = self.config.get('user_config', {}).get('webhook', {}).get('serverchan', {}).get('sc_key')
            if not sc_key:
                self.logger.error("Server酱sc_key未配置")
                return False
            tags_dict = {"tags": tags} if tags else {}
            response = sc_send(sc_key, title, desp, tags_dict)
            success = response.get('code') == 0  # Server酱返回code=0表示成功
            if success:
                self.logger.info(f'Server酱消息发送成功: {title}')
            else:
                self.logger.error(f'Server酱消息发送失败: {response.get("message")})')
            return success
        except Exception as e:
            self.logger.exception(f'Server酱消息发送异常: {str(e)}')
            return False
    
    # 初始化qbit_client
    def init_qbit_client(self):
        try:
            self.host = self.config.get('user_config', {}).get('qbittorrent', {}).get('host')
            self.username = self.config.get('user_config', {}).get('qbittorrent', {}).get('username')
            self.password = self.config.get('user_config', {}).get('qbittorrent', {}).get('password')
            self.qbit_client = qbittorrentapi.Client(host=self.host, username=self.username, password=self.password)
            self.qbit_client.auth_log_in()
            if not self.qbit_client.is_logged_in:
                raise Exception('登录验证失败')
            self.logger.info(f"成功连接到qBittorrent，版本：{self.qbit_client.app_version()}")
            return True
        except Exception as e:
            self.logger.error(f"初始化qBittorrent客户端失败: {str(e)}")
            return False

    def init_torrent_dict(self):
        """初始化torrent字典"""
        try:
            self.torrent_dict = {}
            torrents = self.qbit_client.torrents_info()
            for torrent in torrents:
                identifier = f"{torrent.save_path}_{torrent.name}_{torrent.size}"
                if identifier not in self.torrent_dict:
                    self.torrent_dict[identifier] = []
                self.torrent_dict[identifier].append(torrent.hash)
            self.logger.info(f"初始化torrent字典完成，共{len(self.torrent_dict)}个唯一标识符")
        except Exception as e:
            self.logger.error(f"初始化torrent字典时发生错误: {str(e)}")

    # 获取种子信息
    def get_dashboard_info(self) -> DashboardInfo:
        """获取用于在dashboard呈现的信息"""
        torrents = self.qbit_client.torrents_info()
        total_torrents = len(torrents)
        total_trackers = 0
        non_working_trackers = 0
        category_counts = {}
        tag_counts = {}

        for torrent in torrents:
            # 统计tracker信息，不统计被禁用的tracker
            trackers = torrent.trackers
            for tracker in trackers:
                if tracker.status == 0:  # 0表示禁用
                    continue
                total_trackers += 1
                if tracker.status != 2:
                    non_working_trackers += 1
            
            # 统计分类信息
            category = torrent.category if torrent.category else "未分类"
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # 统计标签信息
            tags = torrent.tags.split(',') if torrent.tags else []
            # 处理空标签情况
            if not tags or (len(tags) == 1 and tags[0] == ''):
                tag_counts["无标签"] = tag_counts.get("无标签", 0) + 1
            else:
                for tag in tags:
                    tag = tag.strip()
                    if tag:  # 只统计非空标签
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # 创建DashboardInfo对象
        dashinfo = DashboardInfo(
            total_torrents=total_torrents,
            total_trackers=total_trackers,
            non_working_trackers=non_working_trackers,
            category_counts=category_counts,
            tag_counts=tag_counts
        )
        self.logger.info(f"Dashboard info: {dashinfo}")
        return dashinfo

    def duplicate_tag_opt_single_torrent_single_rule(self, torrent, rule) -> Dict[str, str]:
        """给单个种子打辅种标签
        Args:
            torrent: 种子对象
            rule: 规则对象
        Returns:
            Dict[str, str]: 返回操作结果状态和详情
        """
        result = {
            'status': '',
            'detail': ''
        }
        try:
            # 获取当前种子的标识符
            identifier = f"{torrent.save_path}_{torrent.name}_{torrent.size}"
            
            # 检查该标识符是否在torrent_dict中且有重复
            if identifier in self.torrent_dict and len(self.torrent_dict[identifier]) > 1:
                # 计算辅种数
                duplicate_count = len(self.torrent_dict[identifier])
                duplicate_tag = f"辅种{duplicate_count}"
                
                self.logger.debug(f"发现重复内容的文件：{identifier}，辅种数：{duplicate_count}")
                
                # 检查当前种子是否已包含该标签
                if duplicate_tag not in torrent.tags:
                    # 为当前种子添加辅种标签
                    self.qbit_client.torrents_add_tags(tags=duplicate_tag, torrent_hashes=torrent.hash)
                    self.logger.info(f"为种子 {torrent.name} 添加辅种标签：{duplicate_tag}")
                    result['status'] = 'processed'
                    result['detail'] = f'为种子 {torrent.name} 添加辅种标签：{duplicate_tag}'
                else:
                    self.logger.info(f"种子 {torrent.name} 已存在辅种标签：{duplicate_tag}，无需重复添加")
                    result['status'] = 'skipped'
                    result['detail'] = f"种子 {torrent.name} 已存在辅种标签：{duplicate_tag}，无需重复添加"
            else:
                self.logger.debug(f"种子 {torrent.name} 没有重复，无需添加辅种标签")
                result['status'] = 'skipped'
                result['detail'] = f"种子 {torrent.name} 没有重复，无需添加辅种标签"
                
        except Exception as e:
            self.logger.exception(f'处理种子 {torrent.name} 的辅种标签时发生错误: {str(e)}')
            result['status'] = 'failed'
            result['detail'] = f'处理种子 {torrent.name} 的辅种标签时发生错误: {str(e)}'
            
        return result
    
    def tag_opt_rule_check(self, torrent: Any, rule: Dict) -> bool:
        """检查当前torrent是否匹配到规则
        
        匹配规则说明：
        1. trackers_match为空表示tracker条件匹配成功
        2. trackers_match内部多个值为'或'关系，匹配任一值即成功
        
        Args:
            torrent: 种子对象
            rule: 规则字典
            
        Returns:
            bool: 是否匹配到规则
        """
        # 获取规则中的匹配条件
        trackers_match = rule.get('trackers', '')
        
        # 标记条件匹配状态，默认为True表示空条件视为匹配成功
        trackers_condition_met = True

        # 检查tracker匹配条件
        if trackers_match:
            trackers = torrent.trackers
            tracker_keywords = [k.strip() for k in trackers_match.split('|') if k.strip()]
            
            # 检查是否有任何tracker关键字匹配（或关系）
            trackers_condition_met = False
            for tracker in trackers:
                if any(keyword in tracker.url for keyword in tracker_keywords):
                    trackers_condition_met = True
                    break
        
        # 两个条件之间是与关系，需要同时满足
        return trackers_condition_met
    
    def tag_opt_single_torrent_single_rule(self, torrent: Any, rule) -> Dict:
        """处理单个种子的单个标签规则
        Args:
            torrent: 种子对象
            rule: 规则
        Returns:
            status: 操作结果：processed, failed, skipped （成功、失败、跳过/无需处理）
            detail: 操作详情
        """
        try:
            result = {
                'status': '',
                'detail': ''
            }
            rule_name = rule.get('rule_name', '未命名规则')
            self.logger.debug(f'处理种子: {torrent.name}, 操作: {rule_name}')
                
             # 检查规则是否匹配
            if self.tag_opt_rule_check(torrent, rule):
                self.logger.debug(f'种子 {torrent.name} 匹配到规则 {rule_name}')
                # 该种子和规则匹配上，则根据规则进行操作
                # 读取该种子的所有tag
                torrent_tags = []
                if hasattr(torrent, 'tags') and torrent.tags:
                    torrent_tags = [t.strip() for t in torrent.tags.split(',') if t.strip()]
                tag_to_process = rule.get('tag', '')
                if rule.get('opt_type') == 'add': # 添加标签
                    if tag_to_process not in torrent_tags:
                        try:
                            self.qbit_client.torrents_add_tags(tags=tag_to_process, torrent_hashes=torrent.hash)
                            result['status'] = 'processed'
                            result['detail'] = f'为种子 {torrent.name} 执行规则 {rule_name} 成功'
                            self.logger.info(f'为种子 {torrent.name} 添加标签: {tag_to_process} (规则: {rule_name})')
                        except Exception as e:
                            result['status'] = 'failed'
                            result['detail'] = f'为种子 {torrent.name} 执行规则 {rule_name} 失败'
                            self.logger.error(f'为种子 {torrent.name} 添加标签 {tag_to_process} 失败: {str(e)}')
                    else:
                        result['status'] = 'skipped'
                        result['detail'] = f'种子 {torrent.name} 已存在标签: {tag_to_process}，无需重复添加'
                        self.logger.debug(f'种子 {torrent.name} 已存在标签: {tag_to_process}，无需重复添加')
                else:  # 移除标签
                    if tag_to_process in torrent_tags:
                        try:
                            self.qbit_client.torrents_remove_tags(tags=tag_to_process, torrent_hashes=torrent.hash)
                            result['status'] = 'processed'
                            result['detail'] = f'为种子 {torrent.name} 执行规则 {rule_name} 成功'
                            self.logger.info(f'从种子 {torrent.name} 移除标签: {tag_to_process} (规则: {rule_name})')
                        except Exception as e:
                            result['status'] = 'failed'
                            result['detail'] = f'为种子 {torrent.name} 执行规则 {rule_name} 失败'
                            self.logger.error(f'从种子 {torrent.name} 移除标签 {tag_to_process} 失败: {str(e)}')
                    else:
                        result['status'] = 'skipped'
                        result['detail'] = f'种子 {torrent.name} 不存在标签: {tag_to_process}，无需移除'
                        self.logger.debug(f'种子 {torrent.name} 不存在标签: {tag_to_process}，无需移除') 
            else:
                result['status'] = 'skipped'
                result['detail'] = f'种子 {torrent.name} 未匹配规则 {rule_name}，无需处理'
            return result
        except Exception as e:
            self.logger.exception(f'处理种子 {torrent.name} 时发生错误: {str(e)}')
            return {
                'status': 'failed',
                'detail': f'处理种子 {torrent.name} 时发生错误'
            }
        
    def tracker_opt_rule_check(self, torrent: Any, rule: Dict) -> bool:
        """检查当前torrent是否匹配到规则
        
        匹配规则说明：
        1. tags_match为空表示标签条件匹配成功
        2. trackers_match为空表示tracker条件匹配成功
        3. tags_match内部多个值为'或'关系，匹配任一值即成功
        4. trackers_match内部多个值为'或'关系，匹配任一值即成功
        5. tags_match和trackers_match之间为'与'关系，需要同时满足
        
        Args:
            torrent: 种子对象
            rule: 规则字典
            
        Returns:
            bool: 是否匹配到规则
        """
        # 获取规则中的匹配条件
        tags_match = rule.get('tags', '')
        trackers_match = rule.get('trackers', '')
        
        # 标记条件匹配状态，默认为True表示空条件视为匹配成功
        tags_condition_met = True
        trackers_condition_met = True
        
        # 检查标签匹配条件
        if tags_match:
            torrent_tags = torrent.tags.split(',') if torrent.tags else []
            tag_keywords = [k.strip() for k in tags_match.split('|') if k.strip()]
            
            # 检查是否有任何标签关键字匹配（或关系）
            tags_condition_met = False
            for tag in torrent_tags:
                tag = tag.strip()
                if any(keyword in tag for keyword in tag_keywords):
                    tags_condition_met = True
                    break
        
        # 检查tracker匹配条件
        if trackers_match:
            trackers = torrent.trackers
            tracker_keywords = [k.strip() for k in trackers_match.split('|') if k.strip()]
            
            # 检查是否有任何tracker关键字匹配（或关系）
            trackers_condition_met = False
            for tracker in trackers:
                if any(keyword in tracker.url for keyword in tracker_keywords):
                    trackers_condition_met = True
                    break
        
        # 两个条件之间是与关系，需要同时满足
        return tags_condition_met and trackers_condition_met
        
    def tracker_opt_single_torrent_single_rule(self, torrent: Any, rule: Dict) -> Dict:
        """处理单个种子的单个跟踪器规则
        Args:
            torrent: 种子对象
            rule: 规则
        Returns:
            status: 操作结果：processed, failed, skipped （成功、失败、跳过/无需处理）
            detail: 操作详情
        """
        try:
            result = {
                'status': '',
                'detail': ''
            }
            rule_name = rule.get('rule_name', '未命名规则')
            self.logger.debug(f'处理种子: {torrent.name}, 操作: {rule_name}')
                
             # 检查规则是否匹配
            if self.tracker_opt_rule_check(torrent, rule):
                self.logger.debug(f'种子 {torrent.name} 匹配到规则 {rule_name}')
                # 该种子和规则匹配上，则根据规则进行操作
                tracker_to_process = rule.get('tracker', '').strip()
                opt_type = rule.get('opt_type', '').lower()
                current_trackers = [t.url for t in torrent.trackers]
                
                if opt_type == 'add': # 添加tracker
                    if tracker_to_process not in current_trackers:
                        try:
                            self.qbit_client.torrents_add_trackers(torrent_hash=torrent.hash, urls=[tracker_to_process])
                            result['status'] = 'processed'
                            result['detail'] = f'为种子 {torrent.name} 执行规则 {rule_name} 成功'
                            self.logger.info(f'为种子 {torrent.name} 添加tracker: {tracker_to_process} (规则: {rule_name})')
                        except Exception as e:
                            result['status'] = 'failed'
                            result['detail'] = f'为种子 {torrent.name} 执行规则 {rule_name} 失败'
                            self.logger.error(f'为种子 {torrent.name} 添加tracker {tracker_to_process} 失败: {str(e)}')
                    else:
                        result['status'] = 'skipped'
                        result['detail'] = f'种子 {torrent.name} 已存在tracker: {tracker_to_process}，无需重复添加'
                        self.logger.debug(f'种子 {torrent.name} 已存在tracker: {tracker_to_process}，无需重复添加 (规则: {rule_name})') 
                elif opt_type == 'remove':  # 移除tracker
                    if tracker_to_process in current_trackers:
                        try:
                            self.qbit_client.torrents_remove_trackers(torrent_hash=torrent.hash, urls=[tracker_to_process])
                            result['status'] = 'processed'
                            result['detail'] = f'为种子 {torrent.name} 执行规则 {rule_name} 成功'
                            self.logger.info(f'从种子 {torrent.name} 移除tracker: {tracker_to_process} (规则: {rule_name})')
                        except Exception as e:
                            result['status'] = 'failed'
                            result['detail'] = f'为种子 {torrent.name} 执行规则 {rule_name} 失败'
                            self.logger.error(f'从种子 {torrent.name} 移除tracker {tracker_to_process} 失败: {str(e)}')
                    else:
                        result['status'] = 'skipped'
                        result['detail'] = f'种子 {torrent.name} 不存在tracker: {tracker_to_process}，无需移除'
                        self.logger.debug(f'种子 {torrent.name} 不存在tracker: {tracker_to_process}，无需移除 (规则: {rule_name})') 
            else:
                result['status'] = 'skipped'
                result['detail'] = f'种子 {torrent.name} 未匹配到规则 {rule_name}，无需处理'
                self.logger.debug(f'种子 {torrent.name} 未匹配到规则 {rule_name}，无需处理') 
            return result
            
        except Exception as e:
            self.logger.exception(f'处理种子 {torrent.name} 时发生错误: {str(e)}')
            return {
                'status': 'failed',
                'detail': f'处理种子 {torrent.name} 时发生错误: {str(e)}'
            }

    def opt_single_torrent(self, torrent, rules) -> Dict:
        """根据传入的rules，处理单个的torrent
        """
        # 初始化结果
        results = {
            'processed_count': 0,
            'processed_details': [],
            'skipped_count': 0,
            'skipped_details': [],
            'failed_count': 0,
            'failed_details': []
        }
        try:
            # 先根据priority排序
            rules.sort(key=lambda x: x.get('priority', 0))
            # 遍历rules
            for rule in rules:
                rule_type = rule.get('rule_type', '')
                result = {
                    'status': '',
                    'detail': ''
                }
                if rule_type == 'tag_opt':
                    result = self.tag_opt_single_torrent_single_rule(torrent, rule)
                elif rule_type == 'tracker_opt':
                    result = self.tracker_opt_single_torrent_single_rule(torrent, rule)
                elif rule_type == 'duplicate_tag_opt':
                    result = self.duplicate_tag_opt_single_torrent_single_rule(torrent, rule)
                else:
                    self.logger.warning(f'未知的规则类型: {rule_type}')
                    continue
                if result['status'] == 'processed':
                    results['processed_count'] += 1
                    results['processed_details'].append(result['detail'])
                elif result['status'] == 'failed':
                    results['failed_count'] += 1
                    results['failed_details'].append(result['detail'])
                elif result['status'] == 'skipped':
                    results['skipped_count'] += 1
                    results['skipped_details'].append(result['detail'])
                else:
                    self.logger.warning(f'未知的操作结果状态: {result["status"]}')
                    continue
                    
            return results
        except Exception as e:
            self.logger.exception(f'处理种子 {torrent.name} 时发生错误: {str(e)}')
            results['failed_count'] += 1
            results['failed_details'].append(f'处理种子 {torrent.name} 时发生错误: {str(e)}')
            return results

    def opt_all_torrent(self, rules) -> Dict:
        """根据传入的rules，处理所有torrent。
        Args:
            rules: 规则列表
        Returns:
            Dict: 包含处理结果的字典
            - processed_count: 实际处理种子数
            - processed_details: 实际处理详情：xx 种子 处理xx 规则；xx 种子 处理xx 规则；
            - skipped_count: 无需处理种子数
            - skipped_details: 无需处理详情：xx 种子 无需处理；xx 种子 无需处理；
            - failed_count: 处理失败种子数
            - failed_details: 处理失败详情：xx 种子 处理失败；xx 种子 处理失败；
        """
        self.logger.info(f'开始处理所有种子')
        # 初始化结果
        results = {
            'processed_count': 0,
            'processed_details': [],
            'skipped_count': 0,
            'skipped_details': [],
            'failed_count': 0,
            'failed_details': []
        }
        
        try:
            # 每次都初始化字典
            self.init_torrent_dict()
            torrents = self.qbit_client.torrents_info()
            self.logger.info(f'共获取到 {len(torrents)} 个种子')

            # 逐个处理种子
            for torrent in torrents:
                result = self.opt_single_torrent(torrent, rules)
                results['processed_count'] += result['processed_count']
                results['processed_details'].extend(result['processed_details'])
                results['skipped_count'] += result['skipped_count']
                results['skipped_details'].extend(result['skipped_details'])
                results['failed_count'] += result['failed_count']
                results['failed_details'].extend(result['failed_details'])
                
            self.logger.info(f'处理完成: 成功{results["processed_count"]}个, 跳过{results["skipped_count"]}个, 失败{results["failed_count"]}个')
            return results
            
        except Exception as e:
            self.logger.exception(f'处理所有种子时发生错误: {str(e)}')
            results['failed_count'] += 1
            results['failed_details'].append(f'处理所有种子时发生错误: {str(e)}')
            return results